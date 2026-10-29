import pytest
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

from .conftest import PASSWORD

pytestmark = pytest.mark.django_db

REGISTER = "/api/auth/register/"
LOGIN = "/api/auth/login/"
LOGOUT = "/api/auth/logout/"
ME = "/api/users/me/"

VALID = {"name": "Ana Ficticia", "email": "ana@example.com", "password": PASSWORD}


# ---------- registro ----------
def test_register_creates_cliente_with_hashed_password(api):
    response = api.post(REGISTER, VALID, format="json")
    assert response.status_code == 201
    assert response.json() == {
        "id": response.json()["id"],
        "name": "Ana Ficticia",
        "email": "ana@example.com",
        "role": "cliente",
    }
    user = get_user_model().objects.get(email="ana@example.com")
    assert user.password != PASSWORD
    assert user.password.startswith("pbkdf2_sha256$")
    assert user.check_password(PASSWORD)


def test_register_never_returns_password(api):
    assert "password" not in api.post(REGISTER, VALID, format="json").json()


def test_register_ignores_role_sent_by_client(api):
    response = api.post(REGISTER, {**VALID, "role": "admin"}, format="json")
    assert response.status_code == 201
    assert response.json()["role"] == "cliente"


def test_register_rejects_duplicate_email_case_insensitive(api, cliente):
    response = api.post(REGISTER, {**VALID, "email": "CLIENTE@example.com"}, format="json")
    assert response.status_code == 400
    assert "email" in response.json()["error"]["fields"]


@pytest.mark.parametrize(
    "override, field",
    [
        ({"email": "no-es-correo"}, "email"),
        ({"name": ""}, "name"),
        ({"password": "corta1"}, "non_field_errors"),
        ({"password": "12345678901"}, "non_field_errors"),
        ({"password": "password123"}, "non_field_errors"),
    ],
)
def test_register_validates_fields(api, override, field):
    response = api.post(REGISTER, {**VALID, **override}, format="json")
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert field in error["fields"]
    assert not get_user_model().objects.exists()


def test_register_requires_all_fields(api):
    response = api.post(REGISTER, {}, format="json")
    assert response.status_code == 400
    assert set(response.json()["error"]["fields"]) == {"name", "email", "password"}


def test_register_rejects_get(api):
    assert api.get(REGISTER).status_code == 405


# ---------- login ----------
def test_login_returns_token_and_user(api, cliente):
    response = api.post(LOGIN, {"email": cliente.email, "password": PASSWORD}, format="json")
    assert response.status_code == 200
    body = response.json()
    assert body["token"] == Token.objects.get(user=cliente).key
    assert body["user"]["email"] == cliente.email
    assert body["user"]["role"] == "cliente"


def test_login_email_is_case_insensitive(api, cliente):
    response = api.post(
        LOGIN, {"email": "Cliente@Example.com", "password": PASSWORD}, format="json"
    )
    assert response.status_code == 200


@pytest.mark.parametrize(
    "credentials",
    [
        {"email": "cliente@example.com", "password": "incorrecta-999"},
        {"email": "nadie@example.com", "password": PASSWORD},
    ],
)
def test_login_wrong_credentials_gives_same_401(api, cliente, credentials):
    response = api.post(LOGIN, credentials, format="json")
    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "authentication_failed",
            "message": "Correo o contraseña incorrectos.",
        }
    }


def test_login_inactive_user_is_rejected(api, cliente):
    cliente.is_active = False
    cliente.save()
    response = api.post(LOGIN, {"email": cliente.email, "password": PASSWORD}, format="json")
    assert response.status_code == 401


def test_login_validates_body(api):
    response = api.post(LOGIN, {"email": "x"}, format="json")
    assert response.status_code == 400
    assert set(response.json()["error"]["fields"]) == {"email", "password"}


# ---------- perfil ----------
def test_me_returns_profile(cliente_api, cliente):
    response = cliente_api.get(ME)
    assert response.status_code == 200
    assert response.json() == {
        "id": cliente.id,
        "name": cliente.name,
        "email": cliente.email,
        "role": "cliente",
    }


def test_me_requires_authentication(api):
    response = api.get(ME)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_me_rejects_invalid_token(api):
    api.credentials(HTTP_AUTHORIZATION="Token token-inventado")
    response = api.get(ME)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_failed"


# ---------- logout ----------
def test_logout_invalidates_token(cliente_api):
    assert cliente_api.post(LOGOUT).status_code == 204
    assert cliente_api.get(ME).status_code == 401
    assert not Token.objects.exists()


def test_logout_requires_authentication(api):
    assert api.post(LOGOUT).status_code == 401


def test_full_flow_register_login_me_logout(api):
    assert api.post(REGISTER, VALID, format="json").status_code == 201
    token = api.post(
        LOGIN, {"email": VALID["email"], "password": PASSWORD}, format="json"
    ).json()["token"]
    api.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    assert api.get(ME).json()["email"] == VALID["email"]
    assert api.post(LOGOUT).status_code == 204
    assert api.get(ME).status_code == 401


# ---------- modelo ----------
def test_superuser_gets_admin_role(db):
    user = get_user_model().objects.create_superuser(
        email="Root@Example.com", password=PASSWORD, name="Root"
    )
    assert (user.email, user.role, user.is_staff) == ("root@example.com", "admin", True)


def test_login_trims_spaces_and_ignores_case(api, cliente):
    response = api.post(
        "/api/auth/login/",
        {"email": f"  {cliente.email.upper()}  ", "password": PASSWORD},
        format="json",
    )
    assert response.status_code == 200


def test_revoked_token_cannot_be_reused(cliente_api):
    assert cliente_api.post("/api/auth/logout/").status_code == 204
    response = cliente_api.get("/api/users/me/")
    assert response.status_code == 401
    assert cliente_api.get("/api/chat/conversations/").status_code == 401
