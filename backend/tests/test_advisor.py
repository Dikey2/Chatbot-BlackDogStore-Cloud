from unittest.mock import patch

import pytest

from chat.models import Conversation, Message

pytestmark = pytest.mark.django_db
CONVERSATIONS = "/api/chat/conversations/"
NO_MATCH = {"answer": "La derivaré a un asesor.", "category": None, "matched": False, "escalate": True}


def reply_url(conversation):
    return f"{CONVERSATIONS}{conversation.id}/reply/"


def close_url(conversation):
    return f"{CONVERSATIONS}{conversation.id}/close/"


@pytest.fixture
def derived(cliente):
    conversation = Conversation.objects.create(user=cliente, status="derivada")
    Message.objects.create(conversation=conversation, sender="cliente", content="¿Precio?")
    return conversation


# ---------- bandeja ----------
@pytest.mark.parametrize("client_fixture", ["asesor_api", "admin_api"])
def test_staff_filters_by_status_and_sees_client_name(request, client_fixture, cliente, derived):
    Conversation.objects.create(user=cliente, status="abierta")
    client = request.getfixturevalue(client_fixture)
    body = client.get(CONVERSATIONS, {"status": "derivada"}).json()
    assert [c["id"] for c in body["results"]] == [derived.id]
    assert body["results"][0]["user_name"] == cliente.name


def test_cliente_status_filter_only_covers_own(cliente_api, make_user, derived):
    Conversation.objects.create(user=make_user("otra@example.com"), status="derivada")
    body = cliente_api.get(CONVERSATIONS, {"status": "derivada"}).json()
    assert [c["id"] for c in body["results"]] == [derived.id]


# ---------- responder ----------
@pytest.mark.parametrize("client_fixture", ["asesor_api", "admin_api"])
def test_staff_reply_is_stored_as_asesor_message(request, client_fixture, derived):
    client = request.getfixturevalue(client_fixture)
    response = client.post(reply_url(derived), {"message": "Le escribo con el precio."}, format="json")
    assert response.status_code == 201
    assert response.json()["sender"] == "asesor"
    assert list(derived.messages.values_list("sender", flat=True)) == ["cliente", "asesor"]


def test_client_sees_advisor_reply_in_latest(cliente_api, asesor_api, derived):
    asesor_api.post(reply_url(derived), {"message": "Respuesta del asesor."}, format="json")
    body = cliente_api.get(f"{CONVERSATIONS}latest/").json()
    assert [(m["sender"], m["content"]) for m in body["messages"]] == [
        ("cliente", "¿Precio?"),
        ("asesor", "Respuesta del asesor."),
    ]


def test_cliente_cannot_reply_even_to_own_conversation(cliente_api, derived):
    response = cliente_api.post(reply_url(derived), {"message": "x"}, format="json")
    assert response.status_code == 403
    assert derived.messages.count() == 1


def test_reply_requires_authentication(api, derived):
    assert api.post(reply_url(derived), {"message": "x"}, format="json").status_code == 401


@pytest.mark.parametrize("body", [{}, {"message": ""}, {"message": "a" * 2001}])
def test_reply_validates(asesor_api, derived, body):
    response = asesor_api.post(reply_url(derived), body, format="json")
    assert response.status_code == 400
    assert derived.messages.count() == 1


def test_reply_to_missing_conversation_gives_404(asesor_api, db):
    response = asesor_api.post(f"{CONVERSATIONS}9999/reply/", {"message": "x"}, format="json")
    assert response.status_code == 404


# ---------- cerrar ----------
def test_advisor_closes_conversation(asesor_api, derived):
    response = asesor_api.post(close_url(derived))
    assert response.status_code == 200
    assert response.json()["status"] == "cerrada"
    derived.refresh_from_db()
    assert derived.status == "cerrada"


def test_closed_conversation_rejects_reply_and_second_close(asesor_api, derived):
    asesor_api.post(close_url(derived))
    reply = asesor_api.post(reply_url(derived), {"message": "x"}, format="json")
    assert reply.status_code == 409
    assert reply.json()["error"]["code"] == "conversation_closed"
    assert asesor_api.post(close_url(derived)).status_code == 409


def test_cliente_cannot_close(cliente_api, derived):
    assert cliente_api.post(close_url(derived)).status_code == 403
    derived.refresh_from_db()
    assert derived.status == "derivada"


def test_client_cannot_continue_closed_conversation_but_can_start_new(cliente_api, asesor_api, derived):
    asesor_api.post(close_url(derived))
    with patch("chat.views.ask_chatbot", return_value=NO_MATCH):
        blocked = cliente_api.post(
            "/api/chat/messages/", {"message": "hola", "conversation_id": derived.id}, format="json"
        )
        assert blocked.status_code == 409
        new = cliente_api.post("/api/chat/messages/", {"message": "hola"}, format="json")
    assert new.status_code == 201
    assert new.json()["conversation"]["id"] != derived.id
    assert cliente_api.get(f"{CONVERSATIONS}latest/").json()["id"] == new.json()["conversation"]["id"]


def test_latest_shows_closed_status_until_client_writes_again(cliente_api, asesor_api, derived):
    asesor_api.post(close_url(derived))
    body = cliente_api.get(f"{CONVERSATIONS}latest/").json()
    assert (body["id"], body["status"]) == (derived.id, "cerrada")
