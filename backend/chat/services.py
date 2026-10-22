"""Cliente HTTP del servicio de chatbot."""
import json
import urllib.error
import urllib.request

from django.conf import settings
from rest_framework.exceptions import APIException


class ChatbotUnavailable(APIException):
    status_code = 503
    default_code = "chatbot_unavailable"
    default_detail = "El chatbot no está disponible. Inténtelo más tarde."


def ask_chatbot(message, faqs):
    """Envía el mensaje y las FAQ activas. Devuelve answer, category, matched y escalate."""
    payload = json.dumps({"message": message, "faqs": faqs}).encode()
    request = urllib.request.Request(
        f"{settings.CHATBOT_SERVICE_URL}/api/reply/",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            return json.load(response)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise ChatbotUnavailable() from exc
