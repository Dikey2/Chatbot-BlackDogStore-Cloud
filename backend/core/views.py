import json
import urllib.request

from django.conf import settings
from django.db import connection
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
    throttle_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


def _database_ok():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return True
    except Exception:
        return False


def _chatbot_ok():
    try:
        url = f"{settings.CHATBOT_SERVICE_URL}/health/"
        with urllib.request.urlopen(url, timeout=2) as response:
            return json.load(response).get("status") == "ok"
    except Exception:
        return False


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([])
def health(request):
    """Verificación de la API y de sus dependencias. 503 si alguna no responde."""
    checks = {"database": _database_ok(), "chatbot": _chatbot_ok()}
    healthy = all(checks.values())
    return Response(
        {
            "status": "ok" if healthy else "degraded",
            "service": "backend",
            "checks": {name: "ok" if ok else "error" for name, ok in checks.items()},
        },
        status=200 if healthy else 503,
    )
