from unittest.mock import patch

import pytest

from .conftest import PASSWORD

pytestmark = pytest.mark.django_db


def test_login_is_blocked_after_10_attempts_per_minute(api, cliente):
    body = {"email": cliente.email, "password": "incorrecta-999"}
    statuses = [api.post("/api/auth/login/", body, format="json").status_code for _ in range(11)]
    assert statuses == [401] * 10 + [429]

    blocked = api.post("/api/auth/login/", {**body, "password": PASSWORD}, format="json")
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "throttled"
    assert int(blocked["Retry-After"]) > 0


def test_register_and_login_share_the_auth_limit(api):
    for _ in range(10):
        api.post("/api/auth/register/", {}, format="json")
    assert api.post("/api/auth/login/", {}, format="json").status_code == 429


def test_anonymous_limit_60_per_minute(api):
    statuses = [api.get("/api/faqs/").status_code for _ in range(61)]
    assert statuses == [200] * 60 + [429]


def test_chat_limit_30_per_minute_per_user(cliente_api, admin_api):
    answer = {"answer": "r", "category": None, "matched": False, "escalate": True}
    with patch("chat.views.ask_chatbot", return_value=answer):
        statuses = [
            cliente_api.post("/api/chat/messages/", {"message": "hola"}, format="json").status_code
            for _ in range(31)
        ]
        assert statuses == [201] * 30 + [429]
        # El límite es por usuario: otro usuario no queda bloqueado.
        other = admin_api.post("/api/chat/messages/", {"message": "hola"}, format="json")
        assert other.status_code == 201


def test_limits_are_per_client_ip(api):
    for _ in range(60):
        api.get("/api/faqs/")
    assert api.get("/api/faqs/").status_code == 429
    assert api.get("/api/faqs/", REMOTE_ADDR="10.0.0.9").status_code == 200


def test_unknown_api_route_gives_404_json(api):
    response = api.get("/api/no-existe/")
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Ruta no encontrada."}}


def test_malformed_json_gives_400(api):
    response = api.post("/api/auth/login/", "{no es json", content_type="application/json")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "parse_error"


def test_unsupported_media_type_gives_415(api):
    response = api.post("/api/auth/login/", "a=1", content_type="text/plain")
    assert response.status_code == 415


def test_404_does_not_reveal_internal_model_names(api, db):
    response = api.get("/api/faqs/9999/")
    assert response.json() == {"error": {"code": "not_found", "message": "Recurso no encontrado."}}


def test_rate_limit_counters_use_shared_database_cache(settings):
    # Varios procesos de gunicorn deben compartir los contadores.
    assert settings.CACHES["default"]["BACKEND"] == "django.core.cache.backends.db.DatabaseCache"
