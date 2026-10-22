from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle, UserRateThrottle
from rest_framework.views import APIView

from core.permissions import STAFF_ROLES, IsStaffRole
from faqs.models import FAQ

from .models import Conversation, Message
from .serializers import (
    AdvisorReplySerializer,
    ConversationDetailSerializer,
    ConversationSerializer,
    MessageSerializer,
    SendMessageSerializer,
)
from .services import ask_chatbot


class ConversationClosed(APIException):
    status_code = 409
    default_code = "conversation_closed"
    default_detail = "La conversación está cerrada."


def conversations_for(user):
    """El cliente ve solo sus conversaciones; asesor y administrador ven todas."""
    queryset = Conversation.objects.select_related("user")
    if user.role in STAFF_ROLES:
        return queryset
    return queryset.filter(user=user)


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
            if conversation.status == Conversation.Status.CERRADA:
                # Tras el cierre del asesor, el cliente empieza una conversación nueva.
                raise ConversationClosed()

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
        queryset = conversations_for(self.request.user)
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

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
            Conversation.objects.filter(user=request.user)
            .select_related("user")
            .prefetch_related("messages")
            .first()
        )
        if conversation is None:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(self.get_serializer(conversation).data)

    @action(detail=True, methods=["post"], permission_classes=[IsStaffRole])
    def reply(self, request, pk=None):
        """Respuesta de un asesor o administrador a una conversación (RF-09)."""
        conversation = self.get_object()
        if conversation.status == Conversation.Status.CERRADA:
            raise ConversationClosed()
        serializer = AdvisorReplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = Message.objects.create(
            conversation=conversation,
            sender=Message.Sender.ASESOR,
            content=serializer.validated_data["message"],
        )
        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[IsStaffRole])
    def close(self, request, pk=None):
        """Marca la conversación como atendida. El cliente seguirá en una nueva."""
        conversation = self.get_object()
        if conversation.status == Conversation.Status.CERRADA:
            raise ConversationClosed()
        conversation.status = Conversation.Status.CERRADA
        conversation.save(update_fields=["status"])
        return Response(ConversationSerializer(conversation).data)
