"""Logs estructurados en JSON (una línea por evento).

Campos comunes: timestamp, level, service, logger, event, request_id.
Según el evento: operation, method, path, status, duration_ms, user_id,
business_id, error_code...

NUNCA se registran contraseñas, tokens, cabeceras de autorización, la query
string (puede llevar datos) ni el contenido de los mensajes del chat.
"""
import contextvars
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone

request_id_var = contextvars.ContextVar("request_id", default=None)

SERVICE = os.environ.get("SERVICE_NAME", "backend")
SLOW_REQUEST_MS = float(os.environ.get("SLOW_REQUEST_MS", "1000"))
_REQUEST_ID_OK = re.compile(r"^[A-Za-z0-9._-]{8,64}$")

# Atributos estándar de LogRecord: lo demás llega por ``extra`` y va al JSON.
_STANDARD = set(vars(logging.LogRecord("", 0, "", 0, "", (), None))) | {"message", "asctime"}
# Claves que jamás se escriben aunque alguien las pase en ``extra``.
_FORBIDDEN = {"password", "token", "authorization", "content", "message_text", "secret"}


class JsonFormatter(logging.Formatter):
    def format(self, record):
        data = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "service": SERVICE,
            "logger": record.name,
            "event": record.getMessage(),
            "request_id": getattr(record, "request_id", None) or request_id_var.get(),
        }
        for key, value in record.__dict__.items():
            if key in _STANDARD or key.startswith("_") or key in data:
                continue
            if key.lower() in _FORBIDDEN:
                continue
            data[key] = value if isinstance(value, (str, int, float, bool, type(None))) else str(value)
        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=False)


def _user_id(request):
    user = getattr(request, "user", None)
    try:
        return user.id if user is not None and user.is_authenticated else None
    except Exception:
        return None


class RequestLogMiddleware:
    """Un log por petición HTTP con su duración. Añade ``X-Request-ID`` a la respuesta."""

    logger = logging.getLogger("http.request")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.headers.get("X-Request-ID", "")
        request_id = incoming if _REQUEST_ID_OK.match(incoming) else uuid.uuid4().hex
        request.request_id = request_id
        token = request_id_var.set(request_id)
        started = time.monotonic()
        response = None
        try:
            response = self.get_response(request)
            return response
        finally:
            duration_ms = round((time.monotonic() - started) * 1000, 1)
            status = response.status_code if response is not None else 500
            if response is not None:
                response["X-Request-ID"] = request_id
            tenant = getattr(request, "_tenant", None)
            level = logging.INFO
            if status >= 500:
                level = logging.ERROR
            elif status >= 400 or duration_ms >= SLOW_REQUEST_MS:
                level = logging.WARNING
            self.logger.log(
                level,
                "slow_request" if duration_ms >= SLOW_REQUEST_MS and status < 400 else "http_request",
                extra={
                    "operation": "http",
                    "method": request.method,
                    # Solo la ruta: la query string puede contener datos del cliente.
                    "path": request.path,
                    "status": status,
                    "duration_ms": duration_ms,
                    "user_id": _user_id(request),
                    "business_id": tenant[0].id if tenant else None,
                },
            )
            request_id_var.reset(token)
