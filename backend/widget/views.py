"""API pública del widget: la usan visitantes anónimos desde la web del negocio.

    GET  /api/widget/<public_id>/config/          apariencia y bienvenida
    POST /api/widget/<public_id>/session/         sesión anónima nueva (token)
    POST /api/widget/<public_id>/session/rotate/  token nuevo; el anterior deja de servir
    GET  /api/widget/<public_id>/conversation/    conversación del visitante (?after=<id>)
    POST /api/widget/<public_id>/messages/        mensaje del visitante y respuesta del bot
    POST /api/widget/<public_id>/handoff/         el visitante pide un asesor

Nada aquí exige cuenta. Un visitante solo ve su propia conversación y solo
dentro del negocio del widget que está usando.
"""
from pathlib import Path

from django.conf import settings
from django.db.models import F
from django.http import HttpResponse
from django.views.decorators.http import require_safe
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.models import AuditEvent
from audit.services import record
from chat.conversation import request_handoff, take_turn
from chat.models import Conversation
from chat.serializers import MessageSerializer
from tenants.models import VisitorSession

from .security import (
    SessionLimitReached,
    WidgetMessageIpThrottle,
    WidgetMessageThrottle,
    WidgetReadThrottle,
    WidgetSessionThrottle,
    visitor_session,
    widget_business,
)

WIDGET_JS = Path(__file__).resolve().parent / "static_src" / "widget.js"


class WidgetMessageSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=500, trim_whitespace=True)


class PublicWidgetView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [WidgetReadThrottle]

    def get_authenticate_header(self, request):
        # Sin esto DRF convierte el 401 de una sesión vencida en 403.
        return "Visitor"


def _conversation_payload(conversation):
    if conversation is None:
        return None
    return {"id": conversation.id, "status": conversation.status}


def _current_conversation(session, business):
    return (
        Conversation.objects.filter(visitor=session, business=business)
        .order_by("-created_at", "-id")
        .first()
    )


class WidgetConfigView(PublicWidgetView):
    def get(self, request, public_id):
        business = widget_business(request, public_id)
        config = business.chatbot
        return Response(
            {
                "business": {"name": business.name, "logo_url": business.logo_url},
                "assistant_name": config.assistant_name,
                "welcome_message": config.welcome_message,
                "primary_color": config.primary_color,
            }
        )


class WidgetSessionView(PublicWidgetView):
    throttle_classes = [WidgetSessionThrottle]

    def post(self, request, public_id):
        business = widget_business(request, public_id)
        session, token = VisitorSession.issue(business, origin=request.headers.get("Origin", ""))
        return Response(
            {"token": token, "expires_at": session.expires_at.isoformat()},
            status=status.HTTP_201_CREATED,
        )


class WidgetRotateView(PublicWidgetView):
    throttle_classes = [WidgetSessionThrottle]

    def post(self, request, public_id):
        business = widget_business(request, public_id)
        session = visitor_session(request, business)
        token = session.rotate()
        return Response({"token": token, "expires_at": session.expires_at.isoformat()})


class WidgetConversationView(PublicWidgetView):
    def get(self, request, public_id):
        business = widget_business(request, public_id)
        session = visitor_session(request, business)
        conversation = _current_conversation(session, business)
        messages = []
        if conversation is not None:
            queryset = conversation.messages.all()
            after = request.query_params.get("after", "")
            if after.isdigit():
                queryset = queryset.filter(id__gt=int(after))
            messages = MessageSerializer(queryset[:100], many=True).data
        return Response({"conversation": _conversation_payload(conversation), "messages": messages})


class WidgetMessageView(PublicWidgetView):
    throttle_classes = [WidgetMessageThrottle, WidgetMessageIpThrottle]

    def post(self, request, public_id):
        business = widget_business(request, public_id)
        session = visitor_session(request, business)
        serializer = WidgetMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if session.message_count >= settings.WIDGET_MAX_MESSAGES_PER_SESSION:
            raise SessionLimitReached()

        conversation = _current_conversation(session, business)
        if conversation is not None and conversation.status == Conversation.Status.CERRADA:
            conversation = None  # tras el cierre, la siguiente consulta abre otra conversación
        turn = take_turn(
            business,
            serializer.validated_data["message"],
            conversation=conversation,
            visitor=session,
            fallback=True,
        )
        VisitorSession.objects.filter(pk=session.pk).update(message_count=F("message_count") + 1)
        if turn["escalated"]:
            record(
                request, AuditEvent.Action.CONVERSACION_DERIVAR,
                detail=f"Conversación {turn['conversation'].id} (widget)", business=business,
            )
        return Response(
            {
                "conversation": _conversation_payload(turn["conversation"]),
                "user_message": MessageSerializer(turn["user_message"]).data,
                "bot_message": MessageSerializer(turn["bot_message"]).data,
                "escalated": turn["escalated"],
                "degraded": turn["degraded"],
            },
            status=status.HTTP_201_CREATED,
        )


class WidgetHandoffView(PublicWidgetView):
    throttle_classes = [WidgetMessageThrottle, WidgetMessageIpThrottle]

    def post(self, request, public_id):
        business = widget_business(request, public_id)
        session = visitor_session(request, business)
        conversation = _current_conversation(session, business)
        if conversation is None or conversation.status == Conversation.Status.CERRADA:
            return Response(
                {"error": {"code": "no_conversation", "message": "Escribe tu consulta primero."}},
                status=status.HTTP_409_CONFLICT,
            )
        bot_message = request_handoff(conversation, business.chatbot.handoff_message)
        if bot_message is not None:
            record(
                request, AuditEvent.Action.CONVERSACION_DERIVAR,
                detail=f"Conversación {conversation.id} (widget, a pedido)", business=business,
            )
        return Response(
            {
                "conversation": _conversation_payload(conversation),
                "bot_message": MessageSerializer(bot_message).data if bot_message else None,
            }
        )


@require_safe
def widget_script(request):
    """Distribuye widget.js. Se cachea poco para que una corrección llegue pronto."""
    response = HttpResponse(WIDGET_JS.read_bytes(), content_type="application/javascript; charset=utf-8")
    response["Cache-Control"] = "public, max-age=300"
    response["X-Content-Type-Options"] = "nosniff"
    # Un sitio de terceros lo carga con <script>: no necesita CORS, pero sí CORP.
    response["Cross-Origin-Resource-Policy"] = "cross-origin"
    return response
