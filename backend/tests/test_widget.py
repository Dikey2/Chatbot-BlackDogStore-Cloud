"""Widget público: visitantes anónimos, origen autorizado, sesiones y abuso."""
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from chat.models import Conversation, Message
from chat.services import ChatbotUnavailable
from faqs.models import FAQ
from tenants.models import Business, BusinessDomain, ChatbotConfig, VisitorSession

pytestmark = pytest.mark.django_db


ORIGIN = "https://tienda.example.com"
OTHER_ORIGIN = "https://cafe.example.com"
MATCH = {"answer": "Abrimos de 9 a 18 (dato del negocio).", "category": "horario", "matched": True, "escalate": False}
NO_MATCH = {"answer": "Lo derivo a un asesor.", "category": None, "matched": False, "escalate": True}


@pytest.fixture
def shop(pilot):
    BusinessDomain.objects.create(business=pilot, origin=ORIGIN)
    return pilot


@pytest.fixture
def cafe(db):
    business = Business.objects.create(slug="cafe-aurora", name="Café Aurora (ficticio)")
    ChatbotConfig.objects.create(business=business, assistant_name="Aurora", primary_color="#7c2d12")
    BusinessDomain.objects.create(business=business, origin=OTHER_ORIGIN)
    FAQ.objects.create(business=business, category="menu", question="Menú", answer="SECRETO-CAFE", keywords="menu")
    return business


def url(business, path):
    return f"/api/widget/{business.public_id}/{path}"


def call(api, method, business, path, origin=ORIGIN, token=None, data=None):
    headers = {"HTTP_ORIGIN": origin} if origin else {}
    if token:
        headers["HTTP_X_VISITOR_TOKEN"] = token
    return getattr(api, method)(url(business, path), data or {}, format="json", **headers)


def new_session(api, business, origin=ORIGIN):
    response = call(api, "post", business, "session/", origin=origin)
    assert response.status_code == 201, response.content
    return response.json()["token"]


def say(api, business, token, text="¿Cuál es el horario?", reply=MATCH, origin=ORIGIN):
    with patch("chat.conversation.ask_chatbot", return_value=reply) as chatbot:
        response = call(api, "post", business, "messages/", origin=origin, token=token, data={"message": text})
    return response, chatbot


# ---------------------------------------------------------------- configuración y origen

def test_config_is_public_for_authorized_origin(api, shop):
    response = call(api, "get", shop, "config/")
    assert response.status_code == 200
    body = response.json()
    assert body["assistant_name"] == "Asistente de Black Dog Store"
    assert set(body) == {"business", "assistant_name", "welcome_message", "primary_color"}
    assert response["Access-Control-Allow-Origin"] == ORIGIN


def test_unauthorized_origin_is_rejected_by_cors(api, shop):
    response = call(api, "get", shop, "config/", origin="https://pirata.example.com")
    assert response.status_code == 403
    assert "Access-Control-Allow-Origin" not in response


def test_origin_of_another_business_is_rejected(api, shop, cafe):
    # El dominio del café no está autorizado para el widget de la tienda.
    assert call(api, "get", shop, "config/", origin=OTHER_ORIGIN).status_code == 403


def test_request_without_origin_is_rejected(api, shop):
    assert call(api, "get", shop, "config/", origin=None).status_code == 403


def test_preflight_allows_visitor_header_only(api, shop):
    response = api.options(
        url(shop, "messages/"), HTTP_ORIGIN=ORIGIN, HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST"
    )
    assert response.status_code == 204
    assert response["Access-Control-Allow-Headers"] == "Content-Type, X-Visitor-Token"
    assert "DELETE" not in response["Access-Control-Allow-Methods"]


def test_unknown_suspended_or_disabled_chatbot_is_404(api, shop):
    assert api.get("/api/widget/bd_inexistente/config/", HTTP_ORIGIN=ORIGIN).status_code in (403, 404)
    shop.chatbot.is_active = False
    shop.chatbot.save()
    assert call(api, "get", shop, "config/").status_code == 404
    shop.chatbot.is_active = True
    shop.chatbot.save()
    shop.is_active = False
    shop.save()
    assert call(api, "get", shop, "config/").status_code in (403, 404)


@override_settings(WIDGET_PREVIEW_ORIGINS=["http://localhost:3010"])
def test_platform_preview_origin_can_load_any_widget(api, cafe):
    assert call(api, "get", cafe, "config/", origin="http://localhost:3010").status_code == 200


# ---------------------------------------------------------------- sesión anónima y chat

def test_visitor_chats_without_account_and_reads_history(api, shop, faq):
    token = new_session(api, shop)
    stored = VisitorSession.objects.get()
    assert stored.token_hash != token and len(stored.token_hash) == 64  # solo el hash
    response, chatbot = say(api, shop, token)
    assert response.status_code == 201
    body = response.json()
    assert body["bot_message"]["content"] == MATCH["answer"]
    assert (body["escalated"], body["degraded"]) == (False, False)
    conversation = Conversation.objects.get()
    assert (conversation.business_id, conversation.user_id, conversation.visitor_id) == (shop.id, None, stored.id)
    # El chatbot recibe solo las FAQ de ESTE negocio.
    assert [f["answer"] for f in chatbot.call_args.args[1]] == [faq.answer]
    history = call(api, "get", shop, "conversation/", token=token).json()
    assert [m["sender"] for m in history["messages"]] == ["cliente", "bot"]
    last = history["messages"][-1]["id"]
    newer = call(api, "get", shop, f"conversation/?after={last}", token=token).json()
    assert newer["messages"] == []


def test_missing_or_invalid_token_is_401(api, shop):
    assert call(api, "get", shop, "conversation/").status_code == 401
    response = call(api, "get", shop, "conversation/", token="inventado")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "visitor_session_invalid"


def test_expired_session_is_rejected(api, shop):
    token = new_session(api, shop)
    VisitorSession.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
    assert call(api, "get", shop, "conversation/", token=token).status_code == 401


def test_rotation_invalidates_previous_token(api, shop):
    token = new_session(api, shop)
    say(api, shop, token)
    rotated = call(api, "post", shop, "session/rotate/", token=token)
    assert rotated.status_code == 200
    new_token = rotated.json()["token"]
    assert call(api, "get", shop, "conversation/", token=token).status_code == 401
    history = call(api, "get", shop, "conversation/", token=new_token).json()
    assert len(history["messages"]) == 2  # misma conversación con el token nuevo


def test_visitor_cannot_read_another_visitor_conversation(api, shop):
    first = new_session(api, shop)
    second = new_session(api, shop)
    say(api, shop, first, "mi dato privado")
    other_view = call(api, "get", shop, "conversation/", token=second).json()
    assert other_view == {"conversation": None, "messages": []}


def test_token_of_one_business_does_not_work_in_another(api, shop, cafe):
    token = new_session(api, shop)
    response = call(api, "get", cafe, "conversation/", origin=OTHER_ORIGIN, token=token)
    assert response.status_code == 401


def test_cafe_widget_never_mixes_data_with_shop(api, shop, cafe, faq):
    shop_token = new_session(api, shop)
    cafe_token = new_session(api, cafe, origin=OTHER_ORIGIN)
    _, shop_bot = say(api, shop, shop_token, "horario")
    _, cafe_bot = say(api, cafe, cafe_token, "menu", origin=OTHER_ORIGIN)
    assert "SECRETO-CAFE" not in str(shop_bot.call_args)
    assert faq.answer not in str(cafe_bot.call_args)
    assert cafe_bot.call_args.args[2]["assistant_name"] == "Aurora"
    assert Conversation.objects.filter(business=shop).count() == 1
    assert Conversation.objects.filter(business=cafe).count() == 1


def test_no_answer_escalates_and_advisor_reply_reaches_visitor(api, shop, asesor_api):
    token = new_session(api, shop)
    response, _ = say(api, shop, token, "algo desconocido", reply=NO_MATCH)
    assert response.json()["escalated"] is True
    conversation = Conversation.objects.get()
    assert conversation.status == "derivada"
    # El asesor del negocio la ve en su bandeja, como "Visitante".
    inbox = asesor_api.get("/api/chat/conversations/", {"status": "derivada"}).json()["results"]
    assert inbox[0]["channel"] == "widget" and inbox[0]["user_name"].startswith("Visitante")
    asesor_api.post(f"/api/chat/conversations/{conversation.id}/take/")
    asesor_api.post(f"/api/chat/conversations/{conversation.id}/reply/", {"message": "Te ayudo yo"}, format="json")
    history = call(api, "get", shop, "conversation/", token=token).json()
    assert history["conversation"]["status"] == "atendiendo"
    assert history["messages"][-1] == {**history["messages"][-1], "sender": "asesor", "content": "Te ayudo yo"}


def test_visitor_requests_human(api, shop):
    token = new_session(api, shop)
    assert call(api, "post", shop, "handoff/", token=token).status_code == 409  # aún sin consulta
    say(api, shop, token)
    response = call(api, "post", shop, "handoff/", token=token)
    assert response.status_code == 200
    assert response.json()["conversation"]["status"] == "derivada"
    assert response.json()["bot_message"]["content"] == shop.chatbot.handoff_message
    again = call(api, "post", shop, "handoff/", token=token)
    assert again.json()["bot_message"] is None  # idempotente


def test_closed_conversation_starts_a_new_one(api, shop, asesor_api):
    token = new_session(api, shop)
    say(api, shop, token)
    conversation = Conversation.objects.get()
    asesor_api.post(f"/api/chat/conversations/{conversation.id}/close/")
    say(api, shop, token, "otra consulta")
    assert Conversation.objects.count() == 2


def test_chatbot_failure_keeps_message_and_escalates(api, shop):
    token = new_session(api, shop)
    with patch("chat.conversation.ask_chatbot", side_effect=ChatbotUnavailable()):
        response = call(api, "post", shop, "messages/", token=token, data={"message": "hola"})
    assert response.status_code == 201
    assert response.json()["degraded"] is True
    assert response.json()["escalated"] is True
    assert Message.objects.filter(sender="cliente", content="hola").exists()
    assert Conversation.objects.get().status == "derivada"


def test_message_validation(api, shop):
    token = new_session(api, shop)
    for bad in ({"message": ""}, {"message": "x" * 501}, {}):
        response = call(api, "post", shop, "messages/", token=token, data=bad)
        assert response.status_code == 400


# ---------------------------------------------------------------- abuso

def test_session_creation_is_rate_limited_per_ip(api, shop):
    statuses = [call(api, "post", shop, "session/").status_code for _ in range(11)]
    assert statuses[:10] == [201] * 10
    assert statuses[10] == 429


def test_messages_are_rate_limited_per_visitor(api, shop):
    token = new_session(api, shop)
    statuses = [say(api, shop, token, f"m{i}")[0].status_code for i in range(21)]
    assert statuses[-1] == 429
    assert statuses[:20] == [201] * 20


@override_settings(WIDGET_MAX_MESSAGES_PER_SESSION=2)
def test_session_message_cap(api, shop):
    token = new_session(api, shop)
    say(api, shop, token)
    say(api, shop, token)
    response, _ = say(api, shop, token)
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "session_message_limit"


# ---------------------------------------------------------------- distribución del script

def test_widget_script_is_served_with_safe_headers(api):
    response = api.get("/widget.js")
    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/javascript")
    assert response["X-Content-Type-Options"] == "nosniff"
    body = response.content.decode()
    assert "attachShadow" in body and "data-chatbot-id" in body
    assert "innerHTML = text" not in body  # los mensajes se escriben con textContent


def test_staff_conversation_lists_hide_other_business_widget_chats(api, cafe, asesor_api):
    token = new_session(api, cafe, origin=OTHER_ORIGIN)
    say(api, cafe, token, "menu", origin=OTHER_ORIGIN)
    assert asesor_api.get("/api/chat/conversations/").json()["results"] == []


def test_visitor_token_is_useless_on_staff_api(api, shop):
    token = new_session(api, shop)
    response = APIClient().get(
        "/api/chat/conversations/", HTTP_AUTHORIZATION=f"Token {token}"
    )
    assert response.status_code == 401
