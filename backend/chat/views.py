from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle, UserRateThrottle
from rest_framework.views import APIView

from faqs.models import FAQ

from .models import Conversation, Message
from .serializers import (
    ConversationDetailSerializer,
    ConversationSerializer,
    MessageSerializer,
    SendMessageSerializer,
)
from .services import ask_chatbot


def conversations_for(user):
    """El cliente ve solo sus conversaciones; asesor y administrador ven todas."""
    if user.role in ("asesor", "admin"):
        return Conversation.objects.all()
    return Conversation.objects.filter(user=user)


class SendMessageView(APIView):
    throttle_classes = [UserRateThrottle, ScopedRateThrottle]
    throttle_scope = "chat"

    def post(self, request):
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        text = serializer.validated_data["message"]
        conversation_id = serializer.validated_data.get("conversation_id")

        conversation = None
        if conversation_id:
            # Solo se continúa una conversación propia; la ajena responde 404.
            conversation = get_object_or_404(
                Conversation, pk=conversation_id, user=request.user
            )

        faqs = [
            {"category": faq.category, "answer": faq.answer, "keywords": faq.keyword_list()}
            for faq in FAQ.objects.filter(is_active=True)
        ]
        # Si el chatbot falla se responde 503 y no se guarda nada.
        reply = ask_chatbot(text, faqs)

        with transaction.atomic():
            if conversation is None:
                conversation = Conversation.objects.create(user=request.user)
            user_message = Message.objects.create(
                conversation=conversation, sender=Message.Sender.CLIENTE, content=text
            )
            bot_message = Message.objects.create(
                conversation=conversation, sender=Message.Sender.BOT, content=reply["answer"]
            )
            if reply["escalate"] and conversation.status == Conversation.Status.ABIERTA:
                conversation.status = Conversation.Status.DERIVADA
                conversation.save(update_fields=["status"])

        return Response(
            {
                "conversation": ConversationSerializer(conversation).data,
                "user_message": MessageSerializer(user_message).data,
                "bot_message": MessageSerializer(bot_message).data,
                "category": reply["category"],
                "escalated": reply["escalate"],
            },
            status=status.HTTP_201_CREATED,
        )


class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    def get_queryset(self):
        return conversations_for(self.request.user)

    def get_serializer_class(self):
        if self.action in ("retrieve", "latest"):
            return ConversationDetailSerializer
        return ConversationSerializer

    @action(detail=False)
    def latest(self, request):
        """Última conversación PROPIA con sus mensajes, para reanudar el chat.

        Filtra siempre por el usuario de la sesión, también para asesor y
        administrador: su chat personal no debe mostrar conversaciones ajenas.
        204 si el usuario aún no tiene conversaciones.
        """
        conversation = (
            Conversation.objects.filter(user=request.user).prefetch_related("messages").first()
        )
        if conversation is None:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(self.get_serializer(conversation).data)
