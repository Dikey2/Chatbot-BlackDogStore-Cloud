"""Registro de auditoría (RF-12) y supervisión del administrador."""
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.authtoken.models import Token

from audit.models import AuditEvent
from chat.models import Conversation

from .conftest import PASSWORD, client_for

pytestmark = pytest.mark.django_db
AUDIT = "/api/audit/"


def actions():
    return list(AuditEvent.objects.order_by("id").values_list("action", "result"))


def test_register_login_logout_are_recorded(api):
    api.post(
        "/api/auth/register/",
        {"name": "Persona", "email": "nueva@example.com", "password": PASSWORD},
        format="json",
    )
    token = api.post(
        "/api/auth/login/", {"email": "nueva@example.com", "password": PASSWORD}, format="json"
    ).json()["token"]
    api.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    api.post("/api/auth/logout/")
    assert actions() == [("registro", "exito"), ("login", "exito"), ("logout", "exito")]
    assert set(AuditEvent.objects.values_list("email", flat=True)) == {"nueva@example.com"}


def test_failed_login_is_recorded_without_password(api, cliente):
    api.post("/api/auth/login/", {"email": cliente.email, "password": "mala-123456"}, format="json")
    event = AuditEvent.objects.get()
    assert (event.action, event.result, event.email, event.user) == (
        "login_fallido", "fallo", cliente.email, None
    )
    assert "mala" not in event.detail


def test_expired_token_is_recorded(cliente):
    token = Token.objects.create(user=cliente)
    Token.objects.filter(pk=token.pk).update(created=timezone.now() - timedelta(hours=9))
    from rest_framework.test import APIClient

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    assert client.get("/api/users/me/").status_code == 401
    assert actions() == [("token_expirado", "fallo")]


def test_denied_access_is_recorded(cliente_api):
    assert cliente_api.post("/api/faqs/", {}, format="json").status_code == 403
    event = AuditEvent.objects.get()
    assert (event.action, event.detail) == ("acceso_denegado", "POST /api/faqs/")


def test_faq_operations_are_recorded(admin_api):
    faq_id = admin_api.post(
        "/api/faqs/",
        {"category": "c", "question": "q", "answer": "a", "keywords": "k"},
        format="json",
    ).json()["id"]
    admin_api.patch(f"/api/faqs/{faq_id}/", {"is_active": False}, format="json")
    admin_api.delete(f"/api/faqs/{faq_id}/")
    assert [a for a, _ in actions()] == ["faq_crear", "faq_editar", "faq_eliminar"]
    assert set(AuditEvent.objects.values_list("detail", flat=True)) == {f"FAQ {faq_id}"}


def test_advisor_reply_and_close_are_recorded(asesor_api, cliente):
    conversation = Conversation.objects.create(user=cliente, status="derivada")
    asesor_api.post(f"/api/chat/conversations/{conversation.id}/reply/", {"message": "Hola"}, format="json")
    asesor_api.post(f"/api/chat/conversations/{conversation.id}/close/")
    assert [a for a, _ in actions()] == ["conversacion_responder", "conversacion_cerrar"]


def test_only_admin_can_read_audit(api, cliente_api, asesor_api, admin_api):
    assert api.get(AUDIT).status_code == 401
    assert cliente_api.get(AUDIT).status_code == 403
    assert asesor_api.get(AUDIT).status_code == 403
    response = admin_api.get(AUDIT)
    assert response.status_code == 200
    assert set(response.json()) == {"count", "next", "previous", "results"}


def test_audit_is_read_only_through_the_api(admin_api, make_user):
    event = AuditEvent.objects.create(action="login", result="exito")
    assert admin_api.post(AUDIT, {}, format="json").status_code == 405
    assert admin_api.patch(f"{AUDIT}{event.id}/", {}, format="json").status_code == 405
    assert admin_api.delete(f"{AUDIT}{event.id}/").status_code == 405
    assert AuditEvent.objects.filter(pk=event.pk).exists()


def test_audit_filters_and_validates(admin_api):
    AuditEvent.objects.create(action="login", result="exito")
    AuditEvent.objects.create(action="login_fallido", result="fallo")
    results = admin_api.get(AUDIT, {"result": "fallo"}).json()["results"]
    assert [r["action"] for r in results] == ["login_fallido"]
    results = admin_api.get(AUDIT, {"action": "login"}).json()["results"]
    assert [r["action"] for r in results] == ["login"]
    assert admin_api.get(AUDIT, {"action": "inventada"}).status_code == 400


def test_audit_newest_first(admin_api):
    first = AuditEvent.objects.create(action="login", result="exito")
    second = AuditEvent.objects.create(action="logout", result="exito")
    ids = [r["id"] for r in admin_api.get(AUDIT).json()["results"]]
    # El propio GET del administrador no genera eventos.
    assert ids == [second.id, first.id]


def test_audit_failure_never_breaks_the_request(api, cliente, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("base de auditoría caída")

    monkeypatch.setattr(AuditEvent.objects, "create", boom)
    response = api.post(
        "/api/auth/login/", {"email": cliente.email, "password": PASSWORD}, format="json"
    )
    assert response.status_code == 200


def test_audit_survives_user_deletion(admin_api, make_user):
    user = make_user("borrar@example.com")
    client_for(user).post("/api/auth/logout/")
    user.delete()
    event = AuditEvent.objects.get(action="logout")
    assert (event.user, event.email) == (None, "borrar@example.com")
