"""Errores esperados del servidor (502, 503, 504) y logs estructurados en JSON."""
import io
import json
import logging
import socket
import urllib.error
from unittest.mock import patch

import pytest
from django.db.utils import OperationalError

from chat.services import ChatbotBadGateway, ChatbotTimeout, ChatbotUnavailable, ask_chatbot
from core.logging import JsonFormatter

from .conftest import PASSWORD

pytestmark = pytest.mark.django_db


def send(api, text="hola"):
    return api.post("/api/chat/messages/", {"message": text}, format="json")


# ---------------------------------------------------------------- servicio del chatbot

def test_chatbot_http_error_is_502(cliente_api):
    error = urllib.error.HTTPError("http://chatbot", 500, "boom", {}, io.BytesIO(b""))
    with patch("chat.services.urllib.request.urlopen", side_effect=error):
        response = send(cliente_api)
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "chatbot_bad_gateway"


def test_chatbot_timeout_is_504_without_retry(cliente_api):
    with patch("chat.services.urllib.request.urlopen", side_effect=socket.timeout("timed out")) as urlopen:
        response = send(cliente_api)
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "chatbot_timeout"
    assert urlopen.call_count == 1


def test_chatbot_connection_refused_retries_once_then_503(cliente_api):
    refused = urllib.error.URLError(ConnectionRefusedError("refused"))
    with patch("chat.services.urllib.request.urlopen", side_effect=refused) as urlopen, \
            patch("chat.services.time.sleep"):
        response = send(cliente_api)
    assert response.status_code == 503
    assert urlopen.call_count == 2


def test_chatbot_recovers_on_retry():
    class Ok:
        def __enter__(self):
            return io.BytesIO(json.dumps({"answer": "ok", "escalate": False}).encode())

        def __exit__(self, *args):
            return False

    refused = urllib.error.URLError(ConnectionResetError("reset"))
    with patch("chat.services.urllib.request.urlopen", side_effect=[refused, Ok()]), \
            patch("chat.services.time.sleep"):
        assert ask_chatbot("hola", [])["answer"] == "ok"


def test_invalid_chatbot_payload_is_502():
    class Bad:
        def __enter__(self):
            return io.BytesIO(b'{"sin": "answer"}')

        def __exit__(self, *args):
            return False

    with patch("chat.services.urllib.request.urlopen", return_value=Bad()):
        with pytest.raises(ChatbotBadGateway):
            ask_chatbot("hola", [])


def test_error_classes_have_expected_status():
    assert (ChatbotBadGateway.status_code, ChatbotUnavailable.status_code, ChatbotTimeout.status_code) == (
        502, 503, 504,
    )


def test_failed_chat_saves_nothing_on_platform_chat(cliente_api):
    from chat.models import Conversation

    with patch("chat.services.urllib.request.urlopen", side_effect=socket.timeout("timed out")):
        send(cliente_api)
    assert Conversation.objects.count() == 0


# ---------------------------------------------------------------- base de datos caída

def test_database_down_is_503_with_retry_after(cliente_api):
    with patch("faqs.views.FAQ.objects.filter", side_effect=OperationalError("conexión rechazada")):
        response = cliente_api.get("/api/faqs/")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "database_unavailable"
    assert response["Retry-After"] == "10"
    assert "rechazada" not in response.content.decode()


# ---------------------------------------------------------------- logs estructurados

@pytest.fixture
def json_logs():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    loggers = [logging.getLogger(n) for n in ("http.request", "audit.events", "chatbot.client", "chat.conversation")]
    for logger in loggers:
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    def lines():
        return [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]

    yield lines
    for logger in loggers:
        logger.removeHandler(handler)


def test_each_request_is_logged_as_json_with_request_id(api, json_logs, db):
    response = api.get("/api/faqs/?search=dato-del-cliente", HTTP_X_REQUEST_ID="prueba-req-123456")
    assert response["X-Request-ID"] == "prueba-req-123456"
    entry = [e for e in json_logs() if e["event"] == "http_request"][-1]
    for field in ("timestamp", "level", "service", "request_id", "operation", "method", "path", "status", "duration_ms"):
        assert field in entry
    assert entry["request_id"] == "prueba-req-123456"
    assert entry["path"] == "/api/faqs/"  # sin la query string
    assert "dato-del-cliente" not in json.dumps(entry)


def test_untrusted_request_id_is_replaced(api, json_logs, db):
    response = api.get("/api/faqs/", HTTP_X_REQUEST_ID="<script>")
    assert response["X-Request-ID"] != "<script>"


def test_login_logs_never_contain_password_or_token(api, cliente, json_logs):
    response = api.post("/api/auth/login/", {"email": cliente.email, "password": PASSWORD}, format="json")
    token = response.json()["token"]
    api.post("/api/auth/login/", {"email": cliente.email, "password": "Incorrecta-999"}, format="json")
    raw = json.dumps(json_logs())
    assert PASSWORD not in raw and "Incorrecta-999" not in raw and token not in raw
    operations = {e.get("operation") for e in json_logs()}
    assert {"audit.login", "audit.login_fallido"} <= operations


def test_errors_and_escalations_are_logged_without_message_text(cliente_api, json_logs):
    with patch("chat.conversation.ask_chatbot", return_value={
        "answer": "derivo", "category": None, "matched": False, "escalate": True,
    }):
        send(cliente_api, "MENSAJE-PRIVADO-DEL-CLIENTE")
    entries = json_logs()
    assert any(e.get("operation") == "chat.escalate" for e in entries)
    assert "MENSAJE-PRIVADO-DEL-CLIENTE" not in json.dumps(entries)


def test_chatbot_failure_is_logged(cliente_api, json_logs):
    with patch("chat.services.urllib.request.urlopen", side_effect=socket.timeout("timed out")):
        send(cliente_api)
    failures = [e for e in json_logs() if e["event"] == "chatbot_service_failure"]
    assert failures and failures[0]["failure"] == "timeout"
    server = [e for e in json_logs() if e["event"] == "http_request"][-1]
    assert (server["status"], server["level"]) == (504, "ERROR")


def test_formatter_drops_forbidden_keys():
    record = logging.LogRecord("x", logging.INFO, "", 0, "evento", (), None)
    record.password = "no-debe-salir"
    record.token = "tampoco"
    record.business_id = 7
    data = json.loads(JsonFormatter().format(record))
    assert "password" not in data and "token" not in data and data["business_id"] == 7
