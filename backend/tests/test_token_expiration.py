from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .conftest import PASSWORD

pytestmark = pytest.mark.django_db
ME = "/api/users/me/"
LOGIN = "/api/auth/login/"


def age(token, hours):
    Token.objects.filter(pk=token.pk).update(created=timezone.now() - timedelta(hours=hours))


def client_with(token):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


def test_token_within_ttl_is_accepted(cliente):
    token = Token.objects.create(user=cliente)
    age(token, 7.9)
    assert client_with(token).get(ME).status_code == 200


def test_expired_token_is_rejected_and_deleted(cliente):
    token = Token.objects.create(user=cliente)
    age(token, 8.1)
    response = client_with(token).get(ME)
    assert response.status_code == 401
    assert response.json() == {
        "error": {"code": "token_expired", "message": "La sesión expiró. Inicie sesión de nuevo."}
    }
    assert not Token.objects.filter(pk=token.pk).exists()


@pytest.mark.parametrize(
    "method, path",
    [
        ("get", "/api/users/me/"),
        ("get", "/api/chat/conversations/"),
        ("get", "/api/chat/conversations/latest/"),
        ("post", "/api/chat/messages/"),
        ("post", "/api/auth/logout/"),
    ],
)
def test_expired_token_blocks_every_protected_route(cliente, method, path):
    token = Token.objects.create(user=cliente)
    age(token, 9)
    response = getattr(client_with(token), method)(path, {"message": "hola"}, format="json")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "token_expired"


def test_expired_admin_token_cannot_write_faqs(make_user):
    token = Token.objects.create(user=make_user("admin@example.com", "admin"))
    age(token, 9)
    response = client_with(token).post(
        "/api/faqs/", {"category": "c", "question": "q", "answer": "a", "keywords": "k"}, format="json"
    )
    assert response.status_code == 401


def test_login_returns_expiry(api, cliente):
    before = timezone.now()
    body = api.post(LOGIN, {"email": cliente.email, "password": PASSWORD}, format="json").json()
    expires_at = timezone.datetime.fromisoformat(body["expires_at"])
    assert before + timedelta(hours=8) - timedelta(seconds=5) <= expires_at
    assert expires_at <= timezone.now() + timedelta(hours=8)


def test_login_reuses_valid_token(api, cliente):
    token = Token.objects.create(user=cliente)
    body = api.post(LOGIN, {"email": cliente.email, "password": PASSWORD}, format="json").json()
    assert body["token"] == token.key


def test_login_replaces_expired_token(api, cliente):
    old = Token.objects.create(user=cliente)
    age(old, 9)
    body = api.post(LOGIN, {"email": cliente.email, "password": PASSWORD}, format="json").json()
    assert body["token"] != old.key
    assert client_with(Token.objects.get(key=body["token"])).get(ME).status_code == 200


def test_ttl_is_configurable(cliente, settings):
    settings.TOKEN_TTL_HOURS = 1
    token = Token.objects.create(user=cliente)
    age(token, 1.5)
    assert client_with(token).get(ME).status_code == 401
