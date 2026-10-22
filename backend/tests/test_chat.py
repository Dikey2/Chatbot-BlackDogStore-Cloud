import json
import urllib.error
from unittest.mock import patch

import pytest

from chat.models import Conversation, Message
from chat.services import ask_chatbot

pytestmark = pytest.mark.django_db
URL = "/api/chat/messages/"
CONVERSATIONS = "/api/chat/conversations/"

MATCH = {"answer": "DATO FICTICIO: de 10:00 a 20:00.", "category": "horarios", "matched": True, "escalate": False}
NO_MATCH = {"answer": "La derivaré a un asesor.", "category": None, "matched": False, "escalate": True}


@pytest.fixture
def chatbot():
    with patch("chat.views.ask_chatbot", return_value=MATCH) as mock:
        yield mock


def send(client, text="¿Cuál es el horario?", **extra):
    return client.post(URL, {"message": text, **extra}, format="json")


def test_first_message_creates_conversation_and_stores_both_messages(
    cliente_api, cliente, chatbot, faq
):
    response = send(cliente_api)
    assert response.status_code == 201
    body = response.json()
    conversation = Conversation.objects.get()
    assert conversation.user == cliente
    assert body["conversation"]["id"] == conversation.id
    assert body["conversation"]["status"] == "abierta"
    assert body["user_message"]["sender"] == "cliente"
    assert body["bot_message"] == {
        "id": body["bot_message"]["id"],
        "sender": "bot",
        "content": MATCH["answer"],
        "created_at": body["bot_message"]["created_at"],
    }
    assert (body["category"], body["escalated"]) == ("horarios", False)
    assert list(conversation.messages.values_list("sender", "content")) == [
        ("cliente", "¿Cuál es el horario?"),
        ("bot", MATCH["answer"]),
    ]


def test_backend_sends_only_active_faqs_to_chatbot(cliente_api, chatbot, faq):
    from faqs.models import FAQ

    FAQ.objects.create(category="x", question="q", answer="a", keywords="k", is_active=False)
    send(cliente_api)
    chatbot.assert_called_once_with(
        "¿Cuál es el horario?",
        [{"category": "horarios", "answer": faq.answer, "keywords": ["horario", "atención"]}],
    )


def test_follow_up_message_reuses_conversation(cliente_api, chatbot):
    first = send(cliente_api).json()["conversation"]["id"]
    second = send(cliente_api, "otra", conversation_id=first)
    assert second.status_code == 201
    assert second.json()["conversation"]["id"] == first
    assert Conversation.objects.count() == 1
    assert Message.objects.count() == 4


def test_unmatched_question_escalates_conversation(cliente_api, chatbot):
    chatbot.return_value = NO_MATCH
    response = send(cliente_api, "¿Precio de la laptop?")
    assert response.status_code == 201
    assert response.json()["escalated"] is True
    assert response.json()["conversation"]["status"] == "derivada"
    assert Conversation.objects.get().status == "derivada"


def test_requires_authentication(api, chatbot):
    assert send(api).status_code == 401
    chatbot.assert_not_called()


@pytest.mark.parametrize(
    "body", [{}, {"message": ""}, {"message": "   "}, {"message": "a" * 501}, {"message": "ok", "conversation_id": "abc"}]
)
def test_validates_body(cliente_api, chatbot, body):
    response = cliente_api.post(URL, body, format="json")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"
    assert not Message.objects.exists()


def test_cannot_post_into_another_users_conversation(cliente_api, make_user, chatbot):
    other = Conversation.objects.create(user=make_user("otra@example.com"))
    response = send(cliente_api, conversation_id=other.id)
    assert response.status_code == 404
    assert not Message.objects.exists()
    chatbot.assert_not_called()


def test_chatbot_down_returns_503_and_stores_nothing(cliente_api):
    with patch("chat.services.urllib.request.urlopen", side_effect=urllib.error.URLError("caído")):
        response = send(cliente_api)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "chatbot_unavailable"
    assert not Conversation.objects.exists()


def test_unexpected_error_returns_500_json_without_details(cliente_api):
    with patch("chat.views.ask_chatbot", side_effect=RuntimeError("detalle interno secreto")):
        response = send(cliente_api)
    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "server_error", "message": "Error interno del servidor."}
    }


def test_ask_chatbot_posts_json_contract():
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(MATCH).encode()

    with patch("chat.services.urllib.request.urlopen", return_value=FakeResponse()) as urlopen:
        assert ask_chatbot("hola", []) == MATCH
    request = urlopen.call_args.args[0]
    assert request.full_url.endswith("/api/reply/")
    assert json.loads(request.data) == {"message": "hola", "faqs": []}


# ---------- historial ----------
def test_cliente_sees_only_own_conversations(cliente_api, cliente, make_user):
    own = Conversation.objects.create(user=cliente)
    other = Conversation.objects.create(user=make_user("otra@example.com"))
    body = cliente_api.get(CONVERSATIONS).json()
    assert [c["id"] for c in body["results"]] == [own.id]
    assert cliente_api.get(f"{CONVERSATIONS}{other.id}/").status_code == 404


@pytest.mark.parametrize("client_fixture", ["asesor_api", "admin_api"])
def test_asesor_and_admin_see_all_conversations(request, client_fixture, cliente):
    Conversation.objects.create(user=cliente)
    client = request.getfixturevalue(client_fixture)
    assert client.get(CONVERSATIONS).json()["count"] == 1


def test_conversation_detail_includes_messages(cliente_api, chatbot):
    conversation_id = send(cliente_api).json()["conversation"]["id"]
    body = cliente_api.get(f"{CONVERSATIONS}{conversation_id}/").json()
    assert [m["sender"] for m in body["messages"]] == ["cliente", "bot"]


def test_conversations_require_authentication_and_are_read_only(api, cliente_api):
    assert api.get(CONVERSATIONS).status_code == 401
    assert cliente_api.post(CONVERSATIONS, {}, format="json").status_code == 405


# ---------- historial para reanudar el chat ----------
LATEST = f"{CONVERSATIONS}latest/"


def test_latest_returns_own_conversation_with_messages_in_order(cliente_api, cliente, chatbot):
    first = send(cliente_api, "primera").json()["conversation"]["id"]
    send(cliente_api, "segunda", conversation_id=first)
    response = cliente_api.get(LATEST)
    assert response.status_code == 200
    body = response.json()
    assert (body["id"], body["user"], body["status"]) == (first, cliente.id, "abierta")
    assert [(m["sender"], m["content"]) for m in body["messages"]] == [
        ("cliente", "primera"),
        ("bot", MATCH["answer"]),
        ("cliente", "segunda"),
        ("bot", MATCH["answer"]),
    ]
    times = [m["created_at"] for m in body["messages"]]
    assert times == sorted(times)


def test_latest_is_persisted_in_database(cliente_api, chatbot):
    conversation_id = send(cliente_api, "¿horario?").json()["conversation"]["id"]
    stored = Message.objects.filter(conversation_id=conversation_id).order_by("created_at", "id")
    assert [m.sender for m in stored] == ["cliente", "bot"]
    assert cliente_api.get(LATEST).json()["id"] == conversation_id


def test_latest_picks_most_recent_conversation(cliente_api, cliente):
    Conversation.objects.create(user=cliente)
    newest = Conversation.objects.create(user=cliente)
    assert cliente_api.get(LATEST).json()["id"] == newest.id


def test_latest_without_conversations_gives_204(cliente_api):
    response = cliente_api.get(LATEST)
    assert response.status_code == 204
    assert response.content == b""


def test_latest_requires_authentication(api):
    assert api.get(LATEST).status_code == 401


@pytest.mark.parametrize("client_fixture", ["cliente_api", "asesor_api", "admin_api"])
def test_latest_never_returns_another_users_conversation(request, client_fixture, make_user):
    # Aunque asesor y administrador pueden listar todas, su chat solo carga las propias.
    other = Conversation.objects.create(user=make_user("otra@example.com"))
    Message.objects.create(conversation=other, sender="cliente", content="dato privado")
    client = request.getfixturevalue(client_fixture)
    response = client.get(LATEST)
    assert response.status_code == 204
    assert b"dato privado" not in response.content


def test_cliente_cannot_read_or_continue_another_users_conversation(
    cliente_api, make_user, chatbot
):
    other = Conversation.objects.create(user=make_user("otra@example.com"))
    Message.objects.create(conversation=other, sender="cliente", content="dato privado")
    detail_response = cliente_api.get(f"{CONVERSATIONS}{other.id}/")
    assert detail_response.status_code == 404
    assert b"dato privado" not in detail_response.content
    assert send(cliente_api, conversation_id=other.id).status_code == 404
    assert other.messages.count() == 1
