"""Plataforma multiempresa: aislamiento entre negocios, roles y superadministrador.

Regla: los datos de un negocio nunca aparecen en otro. Cada prueba de acceso
cruzado espera la misma respuesta que para un recurso inexistente (404) o un
rechazo explícito (403), nunca los datos.
"""
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model

from audit.models import AuditEvent
from chat.models import Conversation, Message
from faqs.models import FAQ
from tenants.models import Business, BusinessDomain, ChatbotConfig, Membership

from .conftest import PASSWORD, client_for

pytestmark = pytest.mark.django_db

MATCH = {"answer": "respuesta", "category": "x", "matched": True, "escalate": False}


@pytest.fixture
def other(db):
    business = Business.objects.create(slug="cafe-aurora", name="Café Aurora (ficticio)")
    ChatbotConfig.objects.create(business=business, assistant_name="Aurora")
    return business


@pytest.fixture
def other_admin(make_user, other):
    return make_user("admin@cafe.example.com", "admin", business=other)


@pytest.fixture
def other_admin_api(other_admin):
    return client_for(other_admin)


@pytest.fixture
def other_data(other):
    faq = FAQ.objects.create(
        business=other, category="menu", question="¿Tienen menú?", answer="SECRETO-AURORA",
        keywords="menu",
    )
    visitor_user = get_user_model().objects.create_user(
        email="cliente@cafe.example.com", password=PASSWORD, name="Cliente Café"
    )
    conversation = Conversation.objects.create(business=other, user=visitor_user, status="derivada")
    Message.objects.create(conversation=conversation, sender="cliente", content="SECRETO-AURORA")
    return {"faq": faq, "conversation": conversation}


def _ids(response):
    return [item["id"] for item in response.json()["results"]]


# ---------------------------------------------------------------- aislamiento

def test_pilot_admin_never_sees_other_business_faqs(admin_api, faq, other_data):
    body = admin_api.get("/api/faqs/").json()
    assert [f["id"] for f in body["results"]] == [faq.id]
    assert "SECRETO-AURORA" not in str(body)


def test_pilot_admin_cannot_edit_or_delete_other_business_faq(admin_api, other_data):
    faq_id = other_data["faq"].id
    assert admin_api.get(f"/api/faqs/{faq_id}/").status_code == 404
    assert admin_api.patch(f"/api/faqs/{faq_id}/", {"answer": "x"}, format="json").status_code == 404
    assert admin_api.delete(f"/api/faqs/{faq_id}/").status_code == 404
    other_data["faq"].refresh_from_db()
    assert other_data["faq"].answer == "SECRETO-AURORA"


def test_advisor_inbox_is_scoped_to_own_business(asesor_api, other_data):
    assert _ids(asesor_api.get("/api/chat/conversations/")) == []
    conversation_id = other_data["conversation"].id
    assert asesor_api.get(f"/api/chat/conversations/{conversation_id}/").status_code == 404
    reply = asesor_api.post(
        f"/api/chat/conversations/{conversation_id}/reply/", {"message": "hola"}, format="json"
    )
    assert reply.status_code == 404
    assert asesor_api.post(f"/api/chat/conversations/{conversation_id}/close/").status_code == 404
    assert Message.objects.filter(conversation_id=conversation_id).count() == 1


def test_selecting_a_foreign_business_by_header_is_rejected(admin_api, other, other_data):
    # El id enviado por el navegador selecciona; no autoriza.
    response = admin_api.get("/api/faqs/", HTTP_X_BUSINESS_ID=str(other.id))
    assert response.status_code == 404
    assert "SECRETO-AURORA" not in response.content.decode()
    assert admin_api.get("/api/business/", HTTP_X_BUSINESS_ID=str(other.id)).status_code == 404
    assert admin_api.get("/api/audit/", HTTP_X_BUSINESS_ID="abc").status_code == 404


def test_faq_created_by_admin_belongs_to_their_business_even_if_body_says_otherwise(
    other_admin_api, other, pilot
):
    response = other_admin_api.post(
        "/api/faqs/",
        {"business": pilot.id, "category": "c", "question": "q", "answer": "a", "keywords": "k"},
        format="json",
    )
    assert response.status_code == 201
    assert FAQ.objects.get(pk=response.json()["id"]).business_id == other.id


def test_audit_is_scoped_to_business(admin_api, other_admin_api, other, pilot):
    AuditEvent.objects.create(business=other, action="login", result="exito", detail="AURORA")
    AuditEvent.objects.create(business=pilot, action="login", result="exito", detail="PILOTO")
    pilot_details = [e["detail"] for e in admin_api.get("/api/audit/").json()["results"]]
    other_details = [e["detail"] for e in other_admin_api.get("/api/audit/").json()["results"]]
    assert "AURORA" not in pilot_details and "PILOTO" in pilot_details
    assert "PILOTO" not in other_details and "AURORA" in other_details


def test_chatbot_only_receives_its_business_faqs(cliente_api, faq, other_data):
    with patch("chat.conversation.ask_chatbot", return_value=MATCH) as chatbot:
        cliente_api.post("/api/chat/messages/", {"message": "horario"}, format="json")
    faqs = chatbot.call_args.args[1]
    assert [f["answer"] for f in faqs] == [faq.answer]


def test_user_with_two_businesses_switches_with_header(make_user, other, pilot, faq, other_data):
    user = make_user("doble@example.com", "asesor")
    Membership.objects.create(user=user, business=other, role="admin")
    api = client_for(user)
    pilot_faqs = api.get("/api/faqs/", HTTP_X_BUSINESS_ID=str(pilot.id)).json()["results"]
    other_faqs = api.get("/api/faqs/", HTTP_X_BUSINESS_ID=str(other.id)).json()["results"]
    assert [f["id"] for f in pilot_faqs] == [faq.id]
    assert [f["id"] for f in other_faqs] == [other_data["faq"].id]
    me = api.get("/api/users/me/", HTTP_X_BUSINESS_ID=str(other.id)).json()
    assert (me["role"], me["business"]["id"]) == ("admin", other.id)
    assert {m["business_id"] for m in me["memberships"]} == {pilot.id, other.id}
    # Asesor en el piloto: no administra FAQ allí, aunque sea admin del otro negocio.
    denied = api.post(
        "/api/faqs/", {"category": "c", "question": "q", "answer": "a", "keywords": "k"},
        format="json", HTTP_X_BUSINESS_ID=str(pilot.id),
    )
    assert denied.status_code == 403


def test_legacy_role_field_grants_nothing_without_membership(db):
    user = get_user_model().objects.create_user(
        email="rol@example.com", password=PASSWORD, name="Sin membresía", role="admin"
    )
    api = client_for(user)
    create = api.post(
        "/api/faqs/", {"category": "c", "question": "q", "answer": "a", "keywords": "k"}, format="json"
    )
    assert create.status_code == 403
    assert api.get("/api/audit/").status_code == 403


# ---------------------------------------------------------------- administrador del negocio

def test_admin_configures_own_chatbot(admin_api, pilot):
    response = admin_api.patch(
        "/api/business/",
        {"description": "Tienda ficticia", "chatbot": {"assistant_name": "Rex", "schedule": "L-V 9-18"}},
        format="json",
    )
    assert response.status_code == 200
    pilot.chatbot.refresh_from_db()
    assert (pilot.chatbot.assistant_name, pilot.chatbot.schedule) == ("Rex", "L-V 9-18")
    assert AuditEvent.objects.filter(action="chatbot_configurar", business=pilot).exists()


def test_admin_cannot_suspend_or_rename_slug(admin_api, pilot):
    admin_api.patch("/api/business/", {"is_active": False, "slug": "otro"}, format="json")
    pilot.refresh_from_db()
    assert (pilot.is_active, pilot.slug) == (True, "black-dog-store")


def test_config_validates_color_and_logo(admin_api):
    bad_color = admin_api.patch("/api/business/", {"chatbot": {"primary_color": "red"}}, format="json")
    assert bad_color.status_code == 400
    bad_logo = admin_api.patch("/api/business/", {"logo_url": "http://inseguro.example.com/a.png"}, format="json")
    assert bad_logo.status_code == 400


def test_advisor_reads_but_cannot_configure(asesor_api):
    assert asesor_api.get("/api/business/").status_code == 200
    assert asesor_api.patch("/api/business/", {"name": "x"}, format="json").status_code == 403
    assert asesor_api.get("/api/business/members/").status_code == 403
    assert asesor_api.get("/api/business/domains/").status_code == 403


def test_cliente_cannot_reach_business_panel(cliente_api):
    for path in ("/api/business/", "/api/business/members/", "/api/business/metrics/"):
        assert cliente_api.get(path).status_code == 403


def test_domains_are_normalized_validated_and_scoped(admin_api, other):
    created = admin_api.post("/api/business/domains/", {"origin": "https://Tienda.Example.com/ruta"}, format="json")
    assert created.status_code == 201
    assert created.json()["origin"] == "https://tienda.example.com"
    duplicate = admin_api.post("/api/business/domains/", {"origin": "https://tienda.example.com"}, format="json")
    assert duplicate.status_code == 400
    for bad in ("ftp://x.com", "https://*.x.com", "https://user:pw@x.com", "no-es-url"):
        assert admin_api.post("/api/business/domains/", {"origin": bad}, format="json").status_code == 400
    foreign = BusinessDomain.objects.create(business=other, origin="https://cafe.example.com")
    assert admin_api.delete(f"/api/business/domains/{foreign.id}/").status_code == 404
    assert BusinessDomain.objects.filter(pk=foreign.pk).exists()


def test_admin_manages_advisors_of_own_business(admin_api, pilot):
    created = admin_api.post(
        "/api/business/members/",
        {"email": "nuevo.asesor@example.com", "name": "Nuevo Asesor", "password": "Asesor-ficticio-987"},
        format="json",
    )
    assert created.status_code == 201
    assert created.json()["role"] == "asesor"
    user = get_user_model().objects.get(email="nuevo.asesor@example.com")
    assert user.check_password("Asesor-ficticio-987")
    weak = admin_api.post(
        "/api/business/members/", {"email": "debil@example.com", "name": "D", "password": "123"}, format="json"
    )
    assert weak.status_code == 400
    member_id = created.json()["id"]
    assert admin_api.delete(f"/api/business/members/{member_id}/").status_code == 204


def test_last_admin_cannot_be_removed(admin_api, pilot):
    admin_membership = pilot.memberships.get(role="admin")
    response = admin_api.delete(f"/api/business/members/{admin_membership.id}/")
    assert response.status_code == 400


def test_admin_cannot_remove_member_of_other_business(admin_api, other_admin):
    membership = other_admin.memberships.get()
    assert admin_api.delete(f"/api/business/members/{membership.id}/").status_code == 404


def test_business_metrics_count_only_own_data(admin_api, faq, other_data, cliente):
    Conversation.objects.create(business=faq.business, user=cliente)
    metrics = admin_api.get("/api/business/metrics/").json()
    assert metrics["conversations_total"] == 1
    assert metrics["faqs_active"] == 1


# ---------------------------------------------------------------- superadministrador

@pytest.fixture
def root_api(db):
    root = get_user_model().objects.create_superuser(email="root@example.com", password=PASSWORD, name="Root")
    return client_for(root)


def test_only_platform_admin_reaches_platform(admin_api, asesor_api, cliente_api, root_api):
    for api in (admin_api, asesor_api, cliente_api):
        assert api.get("/api/platform/businesses/").status_code == 403
        assert api.get("/api/platform/metrics/").status_code == 403
    assert root_api.get("/api/platform/businesses/").status_code == 200


def test_platform_admin_creates_business_with_admin_and_config(root_api):
    created = root_api.post(
        "/api/platform/businesses/",
        {"slug": "libreria-sol", "name": "Librería Sol (ficticia)", "description": "Demo"},
        format="json",
    )
    assert created.status_code == 201, created.json()
    business_id = created.json()["id"]
    assert created.json()["public_id"].startswith("bd_")
    assert created.json()["chatbot"]["assistant_name"] == "Asistente de Librería Sol (ficticia)"
    admin = root_api.post(
        f"/api/platform/businesses/{business_id}/admins/",
        {"email": "admin@libreria.example.com", "name": "Admin Librería", "password": "Libreria-ficticia-55"},
        format="json",
    )
    assert admin.status_code == 201
    assert Membership.objects.filter(business_id=business_id, role="admin").count() == 1
    assert AuditEvent.objects.filter(action="negocio_crear", business_id=business_id).exists()


def test_suspended_business_stops_operating(root_api, other, other_admin_api):
    assert root_api.post(f"/api/platform/businesses/{other.id}/suspend/").status_code == 200
    response = other_admin_api.get("/api/faqs/")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "business_suspended"
    assert root_api.post(f"/api/platform/businesses/{other.id}/activate/").status_code == 200
    assert other_admin_api.get("/api/faqs/").status_code == 200


def test_platform_metrics_are_global(root_api, faq, other_data):
    data = root_api.get("/api/platform/metrics/").json()
    assert data["businesses_total"] >= 2
    assert data["faqs_total"] >= 2


def test_existing_staff_got_memberships_in_pilot(db, pilot):
    # La migración de datos convierte el rol heredado en membresía del piloto.
    assert pilot.chatbot.assistant_name == "Asistente de Black Dog Store"



def test_platform_audit_sees_platform_events_only_for_superadmin(root_api, admin_api, api, other, pilot):
    api.post("/api/auth/login/", {"email": "nadie@example.com", "password": "x" * 12}, format="json")
    AuditEvent.objects.create(business=other, action="login", result="exito", detail="AURORA")
    assert admin_api.get("/api/platform/audit/").status_code == 403
    platform_only = root_api.get("/api/platform/audit/", {"business": "none"}).json()["results"]
    assert [e["action"] for e in platform_only] == ["login_fallido"]
    assert platform_only[0]["business"] is None
    other_only = root_api.get("/api/platform/audit/", {"business": other.id}).json()["results"]
    assert [e["detail"] for e in other_only] == ["AURORA"]
    assert other_only[0]["business_name"] == other.name
    assert root_api.get("/api/platform/audit/", {"business": "x"}).status_code == 400
