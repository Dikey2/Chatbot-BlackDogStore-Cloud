"""Cliente HTTP del servicio de chatbot y armado de su conocimiento por negocio.

Errores del servicio, cada uno con su código HTTP:

- 502: el servicio respondió, pero con error o con datos inválidos.
- 503: no se pudo conectar (caído o reiniciándose).
- 504: no respondió dentro del tiempo límite.

Pedir una respuesta no escribe nada en el servicio, así que repetir la petición
es seguro: se reintenta UNA vez solo si la conexión falló (rechazada o cortada).
Un timeout no se reintenta: duplicaría la espera del cliente.
"""
import json
import logging
import socket
import time
import urllib.error
import urllib.request

from django.conf import settings
from rest_framework.exceptions import APIException

logger = logging.getLogger("chatbot.client")

TIMEOUT_SECONDS = 3
RETRY_DELAY_SECONDS = 0.2


class ChatbotUnavailable(APIException):
    status_code = 503
    default_code = "chatbot_unavailable"
    default_detail = "El chatbot no está disponible. Inténtelo más tarde."


class ChatbotBadGateway(ChatbotUnavailable):
    status_code = 502
    default_code = "chatbot_bad_gateway"
    default_detail = "El chatbot respondió con un error. Inténtelo más tarde."


class ChatbotTimeout(ChatbotUnavailable):
    status_code = 504
    default_code = "chatbot_timeout"
    default_detail = "El chatbot tardó demasiado en responder. Inténtelo de nuevo."


def knowledge_for(business):
    """FAQ activas del negocio más la información que el propio negocio configuró.

    El horario y el contacto solo existen para el bot si el negocio los escribió:
    sin dato configurado, el bot no los menciona y deriva.
    """
    faqs = [
        {"category": faq.category, "answer": faq.answer, "keywords": faq.keyword_list()}
        for faq in business.faqs.filter(is_active=True).only("category", "answer", "keywords")
    ]
    config = getattr(business, "chatbot", None)
    if config is not None and config.schedule.strip():
        faqs.append({
            "category": "horario",
            "answer": config.schedule.strip(),
            "keywords": ["horario", "horarios", "hora", "abren", "cierran", "atienden", "atencion"],
        })
    if config is not None and config.contact_info.strip():
        faqs.append({
            "category": "contacto",
            "answer": config.contact_info.strip(),
            "keywords": ["contacto", "telefono", "correo", "email", "whatsapp", "direccion", "ubicacion"],
        })
    return faqs


def bot_settings_for(business):
    config = getattr(business, "chatbot", None)
    if config is None:
        return {"business_name": business.name}
    return {
        "business_name": business.name,
        "assistant_name": config.assistant_name,
        "no_answer_message": config.no_answer_message,
        "handoff_message": config.handoff_message,
        "handoff_keywords": config.handoff_keyword_list(),
    }


def _post(url, payload):
    request = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return json.load(response)


def _is_timeout(exc):
    reason = getattr(exc, "reason", exc)
    return isinstance(reason, (TimeoutError, socket.timeout)) or "timed out" in str(reason)


def ask_chatbot(message, faqs, bot_settings=None):
    """Devuelve answer, category, matched y escalate. Lanza 502/503/504 si falla."""
    body = {"message": message, "faqs": faqs}
    if bot_settings:
        body["settings"] = bot_settings
    payload = json.dumps(body).encode()
    url = f"{settings.CHATBOT_SERVICE_URL}/api/reply/"
    started = time.monotonic()
    for attempt in (1, 2):
        try:
            reply = _post(url, payload)
        except urllib.error.HTTPError as exc:
            _log_failure("bad_gateway", attempt, started, status=exc.code)
            raise ChatbotBadGateway() from exc
        except ValueError as exc:
            _log_failure("invalid_response", attempt, started)
            raise ChatbotBadGateway() from exc
        except (TimeoutError, OSError) as exc:
            if _is_timeout(exc):
                _log_failure("timeout", attempt, started)
                raise ChatbotTimeout() from exc
            if attempt == 1:
                time.sleep(RETRY_DELAY_SECONDS)
                continue
            _log_failure("unavailable", attempt, started)
            raise ChatbotUnavailable() from exc
        if not isinstance(reply, dict) or "answer" not in reply:
            _log_failure("invalid_response", attempt, started)
            raise ChatbotBadGateway()
        return reply
    raise ChatbotUnavailable()  # pragma: no cover


def _log_failure(kind, attempt, started, status=None):
    logger.warning(
        "chatbot_service_failure",
        extra={
            "operation": "chatbot.reply",
            "failure": kind,
            "attempt": attempt,
            "upstream_status": status,
            "duration_ms": round((time.monotonic() - started) * 1000, 1),
        },
    )
