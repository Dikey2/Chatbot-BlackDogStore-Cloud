"""Paginación configurable, filtros, orden y ausencia de consultas N+1."""
import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from chat.models import Conversation, Message
from faqs.models import FAQ

pytestmark = pytest.mark.django_db
CONVERSATIONS = "/api/chat/conversations/"


def many_conversations(make_user, n=30, status="derivada", prefix="u"):
    users = [make_user(f"{prefix}{i}@example.com") for i in range(n)]
    return [Conversation.objects.create(user=u, status=status) for u in users]


def test_page_size_is_configurable_with_upper_limit(api):
    FAQ.objects.bulk_create(
        FAQ(category="c", question=f"p{i}", answer="r", keywords="k") for i in range(120)
    )
    assert len(api.get("/api/faqs/").json()["results"]) == 20
    assert len(api.get("/api/faqs/", {"page_size": 5}).json()["results"]) == 5
    # Límite seguro: nunca más de 100 por página.
    assert len(api.get("/api/faqs/", {"page_size": 1000}).json()["results"]) == 100


def test_pagination_metadata_and_navigation(asesor_api, make_user):
    many_conversations(make_user, 25)
    first = asesor_api.get(CONVERSATIONS, {"status": "derivada", "page_size": 10}).json()
    assert first["count"] == 25
    assert first["previous"] is None and "page=2" in first["next"]
    last = asesor_api.get(CONVERSATIONS, {"status": "derivada", "page_size": 10, "page": 3}).json()
    assert len(last["results"]) == 5 and last["next"] is None
    assert asesor_api.get(CONVERSATIONS, {"page": 99}).status_code == 404


def test_conversations_ordering(asesor_api, make_user):
    created = many_conversations(make_user, 3)
    newest_first = [c["id"] for c in asesor_api.get(CONVERSATIONS).json()["results"]]
    oldest_first = [c["id"] for c in asesor_api.get(CONVERSATIONS, {"ordering": "created_at"}).json()["results"]]
    assert newest_first == [c.id for c in reversed(created)]
    assert oldest_first == [c.id for c in created]


def test_unknown_status_is_a_validation_error(asesor_api):
    response = asesor_api.get(CONVERSATIONS, {"status": "inventado"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


def test_faq_search_and_ordering(api):
    FAQ.objects.create(category="b", question="Horario de tienda", answer="r", keywords="horario")
    FAQ.objects.create(category="a", question="Garantía", answer="r", keywords="garantía")
    assert [f["question"] for f in api.get("/api/faqs/", {"search": "horario"}).json()["results"]] == [
        "Horario de tienda"
    ]
    ordered = [f["category"] for f in api.get("/api/faqs/", {"ordering": "-category"}).json()["results"]]
    assert ordered == ["b", "a"]


def test_inbox_query_count_does_not_grow_with_rows(asesor_api, make_user):
    many_conversations(make_user, 5)
    with CaptureQueriesContext(connection) as small:
        asesor_api.get(CONVERSATIONS, {"status": "derivada"})
    many_conversations(make_user, 20, prefix="otro")
    with CaptureQueriesContext(connection) as large:
        asesor_api.get(CONVERSATIONS, {"status": "derivada"})
    # Nombre del cliente con select_related: sin una consulta por fila.
    assert len(large) == len(small)


def test_conversation_detail_loads_messages_in_one_query(asesor_api, cliente):
    conversation = Conversation.objects.create(user=cliente)
    Message.objects.bulk_create(
        Message(conversation=conversation, sender="cliente", content=str(i)) for i in range(30)
    )
    with CaptureQueriesContext(connection) as queries:
        response = asesor_api.get(f"{CONVERSATIONS}{conversation.id}/")
    assert len(response.json()["messages"]) == 30
    message_queries = [q for q in queries if "chat_message" in q["sql"]]
    assert len(message_queries) == 1


def test_indexes_exist_in_postgresql():
    with connection.cursor() as cursor:
        cursor.execute(
            "select indexname from pg_indexes where tablename in "
            "('chat_conversation', 'chat_message', 'audit_auditevent')"
        )
        names = {row[0] for row in cursor.fetchall()}
    assert {
        "conv_estado_fecha_idx",
        "conv_usuario_fecha_idx",
        "msg_conv_fecha_idx",
        "audit_recientes_idx",
        "audit_accion_idx",
    } <= names
