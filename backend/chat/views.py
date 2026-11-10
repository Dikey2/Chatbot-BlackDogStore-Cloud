from django.shortcuts import get_object_or_404
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle, UserRateThrottle
from rest_framework.views import APIView

from audit.models import AuditEvent
from audit.services import record
from core.permissions import STAFF_ROLES, IsStaffRole
from tenants.context import resolve

from .conversation import take_turn
from .models import Conversation, Message
from .serializers import (
    AdvisorReplySerializer,
    ConversationDetailSerializer,
    ConversationSerializer,
    ConversationStatusSerializer,
    MessageSerializer,
    SendMessageSerializer,
)


class ConversationClosed(APIException):
    status_code = 409
    default_code = "conversation_closed"
    default_detail = "La conversación está cerrada."


class ChatbotDisabled(APIException):
    status_code = 503
    default_code = "chatbot_disabled"
    default_detail = "El chatbot de este negocio está desactivado."


def conversations_for(request):
    """Siempre dentro del negocio resuelto. El cliente ve solo las suyas;
    asesor y administrador, todas las del negocio (y de ningún otro)."""
    business, role = resolve(request)
    queryset = Conversation.objects.filter(business=business).select_related(
        "user", "assigned_to"
    )
    if role in STAFF_ROLES:
        return queryset
    return queryset.filter(user=request.user)


class SendMessageView(APIView):
    """Chat de clientes registrados en la plataforma (negocio piloto o el seleccionado)."""

    throttle_classes = [UserRateThrottle, ScopedRateThrottle]
    throttle_scope = "chat"

    def post(self, request):
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        text = serializer.validated_data["message"]
        conversation_id = serializer.validated_data.get("conversation_id")
        business, _ = resolve(request)
        config = getattr(business, "chatbot", None)
        if config is not None and not config.is_active:
            raise ChatbotDisabled()

        conversation = None
        if conversation_id:
            # Solo se continúa una conversación propia del mismo negocio; otra responde 404.
            conversation = get_object_or_404(
                Conversation, pk=conversation_id, user=request.user, business=business
            )
            if conversation.status == Conversation.Status.CERRADA:
                # Tras el cierre del asesor, el cliente empieza una conversación nueva.
                raise ConversationClosed()

        # Si el chatbot falla se responde 502/503/504 y no se guarda nada.
        turn = take_turn(business, text, conversation=conversation, user=request.user)
        if turn["escalated"]:
            record(
                request,
                AuditEvent.Action.CONVERSACION_DERIVAR,
                detail=f"Conversación {turn['conversation'].id}",
                business=business,
            )
        return Response(
            {
                "conversation": ConversationSerializer(turn["conversation"]).data,
                "user_message": MessageSerializer(turn["user_message"]).data,
                "bot_message": MessageSerializer(turn["bot_message"]).data,
                "category": turn["category"],
                "escalated": turn["escalated"],
            },
            status=status.HTTP_201_CREATED,
        )


class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    # ?ordering=created_at | -created_at (por defecto, más recientes primero).
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["created_at", "id"]

    def get_queryset(self):
        queryset = conversations_for(self.request)
        params = self.request.query_params
        status_filter = params.get("status")
        if status_filter:
            if status_filter not in Conversation.Status.values:
                raise ValidationError({"status": ["Estado desconocido."]})
            queryset = queryset.filter(status=status_filter)
        if params.get("assigned") == "me":
            queryset = queryset.filter(assigned_to=self.request.user)
        if self.action == "retrieve":
            # Una sola consulta extra para todos los mensajes (sin N+1).
            queryset = queryset.prefetch_related("messages")
        return queryset

    def get_serializer_class(self):
        if self.action in ("retrieve", "latest"):
            return ConversationDetailSerializer
        return ConversationSerializer

    @action(detail=False)
    def latest(self, request):
        """Última conversación PROPIA con sus mensajes, para reanudar el chat.

        Filtra siempre por el usuario de la sesión y el negocio resuelto, también
        para asesor y administrador: su chat personal no muestra conversaciones
        ajenas. 204 si el usuario aún no tiene conversaciones.
        """
        business, _ = resolve(request)
        conversation = (
            Conversation.objects.filter(user=request.user, business=business)
            .select_related("user", "assigned_to")
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
        if conversation.assigned_to_id is None:
            # Quien responde primero queda a cargo.
            conversation.assigned_to = request.user
            conversation.save(update_fields=["assigned_to"])
        record(
            request,
            AuditEvent.Action.CONVERSACION_RESPONDER,
            detail=f"Conversación {conversation.id}",
        )
        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[IsStaffRole])
    def take(self, request, pk=None):
        """El asesor toma la conversación: queda asignada a él y 'en atención'."""
        conversation = self.get_object()
        if conversation.status == Conversation.Status.CERRADA:
            raise ConversationClosed()
        conversation.assigned_to = request.user
        conversation.status = Conversation.Status.ATENDIENDO
        conversation.save(update_fields=["assigned_to", "status"])
        record(
            request,
            AuditEvent.Action.CONVERSACION_ASIGNAR,
            detail=f"Conversación {conversation.id}",
        )
        return Response(ConversationSerializer(conversation).data)

    @action(detail=True, methods=["post"], url_path="status", permission_classes=[IsStaffRole])
    def change_status(self, request, pk=None):
        """Cambia el estado de atención (abierta, derivada, atendiendo). Cerrar usa /close/."""
        conversation = self.get_object()
        if conversation.status == Conversation.Status.CERRADA:
            raise ConversationClosed()
        serializer = ConversationStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversation.status = serializer.validated_data["status"]
        conversation.save(update_fields=["status"])
        record(
            request,
            AuditEvent.Action.CONVERSACION_ASIGNAR,
            detail=f"Conversación {conversation.id}: {conversation.status}",
        )
        return Response(ConversationSerializer(conversation).data)

    @action(detail=True, methods=["post"], permission_classes=[IsStaffRole])
    def close(self, request, pk=None):
        """Marca la conversación como atendida. El cliente seguirá en una nueva."""
        conversation = self.get_object()
        if conversation.status == Conversation.Status.CERRADA:
            raise ConversationClosed()
        conversation.status = Conversation.Status.CERRADA
        conversation.save(update_fields=["status"])
        record(
            request,
            AuditEvent.Action.CONVERSACION_CERRAR,
            detail=f"Conversación {conversation.id}",
        )
        return Response(ConversationSerializer(conversation).data)
