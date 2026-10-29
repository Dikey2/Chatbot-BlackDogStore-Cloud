"""CORS con lista explícita de orígenes (core/middleware.py)."""
import pytest

pytestmark = pytest.mark.django_db
ALLOWED = "https://frontend.example.com"
FAQS = "/api/faqs/"


@pytest.fixture(autouse=True)
def allowed_origins(settings):
    settings.CORS_ALLOWED_ORIGINS = [ALLOWED]


def test_request_without_origin_is_not_affected(api):
    # Así llama el servidor de Next.js, curl o Locust.
    response = api.get(FAQS)
    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response


def test_allowed_origin_gets_cors_headers(api):
    response = api.get(FAQS, HTTP_ORIGIN=ALLOWED)
    assert response.status_code == 200
    assert response["Access-Control-Allow-Origin"] == ALLOWED
    assert "Origin" in response["Vary"]
    # La API no usa cookies: nunca se permiten credenciales del navegador.
    assert "Access-Control-Allow-Credentials" not in response


@pytest.mark.parametrize("origin", ["https://evil.example.com", "null", "http://frontend.example.com"])
def test_unexpected_origin_is_rejected_with_403(api, origin):
    response = api.get(FAQS, HTTP_ORIGIN=origin)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "origin_not_allowed"
    assert "Access-Control-Allow-Origin" not in response


def test_unexpected_origin_cannot_write_even_with_valid_token(admin_api):
    response = admin_api.post(
        FAQS,
        {"category": "c", "question": "q", "answer": "a", "keywords": "k"},
        format="json",
        HTTP_ORIGIN="https://evil.example.com",
    )
    assert response.status_code == 403
    from faqs.models import FAQ

    assert FAQ.objects.count() == 0


def test_preflight_from_allowed_origin(api):
    response = api.options(
        FAQS,
        HTTP_ORIGIN=ALLOWED,
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization, content-type",
    )
    assert response.status_code == 204
    assert response["Access-Control-Allow-Origin"] == ALLOWED
    methods = {m.strip() for m in response["Access-Control-Allow-Methods"].split(",")}
    assert {"GET", "POST", "PATCH", "DELETE"} <= methods
    assert "TRACE" not in methods
    headers = {h.strip().lower() for h in response["Access-Control-Allow-Headers"].split(",")}
    assert headers == {"authorization", "content-type"}
    assert response["Access-Control-Max-Age"] == "600"


def test_preflight_from_unexpected_origin_is_rejected(api):
    response = api.options(
        FAQS, HTTP_ORIGIN="https://evil.example.com", HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST"
    )
    assert response.status_code == 403


def test_same_origin_requests_are_allowed(api):
    # Por ejemplo, formularios del panel /admin/ de Django servidos por la propia API.
    response = api.get(FAQS, HTTP_ORIGIN="http://testserver")
    assert response.status_code == 200


def test_cors_does_not_replace_authentication(api):
    # Un origen permitido sigue necesitando token para rutas protegidas.
    response = api.get("/api/users/me/", HTTP_ORIGIN=ALLOWED)
    assert response.status_code == 401


def test_wildcard_is_refused_in_production(monkeypatch):
    import importlib

    import config.settings as settings_module
    from django.core.exceptions import ImproperlyConfigured

    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")
    monkeypatch.setenv("DJANGO_DEBUG", "false")
    with pytest.raises(ImproperlyConfigured):
        importlib.reload(settings_module)
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS")
    importlib.reload(settings_module)
