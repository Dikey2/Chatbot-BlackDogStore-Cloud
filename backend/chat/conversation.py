"""Un turno de conversación: mensaje del cliente, respuesta del bot y derivación.

Lo usan el chat de clientes registrados (``chat.views``) y el widget público
(``widget.views``), para que ambos respondan y deriven exactamente igual.
"""
import logging

from django.db import transaction

from .models import Conversation, Message
from .services import ChatbotUnavailable, ask_chatbot, bot_settings_for, knowledge_for

logger = logging.getLogger("chat.conversation")

DEGRADED_ANSWER = (
    "En este momento no puedo responder automáticamente. "
    "Un asesor revisará tu consulta y te responderá por este chat."
)


def take_turn(business, text, *, conversation=None, user=None, visitor=None, fallback=False):
    """Guarda el mensaje y la respuesta del bot. Devuelve un dict con todo lo creado.

    ``fallback=False`` (chat de la plataforma): si el chatbot falla se propaga el
    error (502/503/504) y no se guarda nada.
    ``fallback=True`` (widget): si el chatbot falla, el mensaje se guarda igual,
    se responde con un aviso y la conversación se deriva a un asesor, para que el
    visitante nunca pierda su consulta.
    """
    degraded = False
    try:
        reply = ask_chatbot(text, knowledge_for(business), bot_settings_for(business))
    except ChatbotUnavailable as exc:
        if not fallback:
            raise
        degraded = True
        reply = {"answer": DEGRADED_ANSWER, "category": None, "matched": False, "escalate": True}
        logger.warning(
            "chatbot_fallback_used",
            extra={"operation": "chat.fallback", "business_id": business.id, "error_code": exc.default_code},
        )

    with transaction.atomic():
        if conversation is None:
            conversation = Conversation.objects.create(business=business, user=user, visitor=visitor)
        user_message = Message.objects.create(
            conversation=conversation, sender=Message.Sender.CLIENTE, content=text
        )
        bot_message = Message.objects.create(
            conversation=conversation, sender=Message.Sender.BOT, content=reply["answer"]
        )
        escalated = bool(reply.get("escalate")) and conversation.status == Conversation.Status.ABIERTA
        if escalated:
            conversation.status = Conversation.Status.DERIVADA
            conversation.save(update_fields=["status"])

    if escalated:
        logger.info(
            "conversation_escalated",
            extra={
                "operation": "chat.escalate",
                "business_id": business.id,
                "conversation_id": conversation.id,
                "reason": "degraded" if degraded else "no_answer_or_rule",
            },
        )
    return {
        "conversation": conversation,
        "user_message": user_message,
        "bot_message": bot_message,
        "category": reply.get("category"),
        "escalated": bool(reply.get("escalate")),
        "degraded": degraded,
    }


def request_handoff(conversation, message):
    """El cliente pide un asesor: se deriva y el bot confirma. Idempotente si ya está derivada."""
    with transaction.atomic():
        bot_message = None
        if conversation.status == Conversation.Status.ABIERTA:
            conversation.status = Conversation.Status.DERIVADA
            conversation.save(update_fields=["status"])
            bot_message = Message.objects.create(
                conversation=conversation, sender=Message.Sender.BOT, content=message
            )
    if bot_message is not None:
        logger.info(
            "conversation_escalated",
            extra={
                "operation": "chat.escalate",
                "business_id": conversation.business_id,
                "conversation_id": conversation.id,
                "reason": "client_request",
            },
        )
    return bot_message
