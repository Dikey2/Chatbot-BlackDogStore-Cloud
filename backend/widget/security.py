"""Seguridad del widget público.

- El negocio se identifica por su ``public_id`` (no es un secreto: solo dice
  qué chatbot cargar). No hay ninguna clave en el JavaScript público.
- Solo los orígenes autorizados por el negocio pueden usar su widget
  (``BusinessDomain``). El navegador envía ``Origin`` y no deja que una página
  lo falsifique; una petición sin ``Origin`` no viene de un navegador y se rechaza.
- El visitante se identifica con un token de sesión anónima (cabecera
  ``X-Visitor-Token``) que solo abre SU conversación. En la base vive el hash.
"""
from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import APIException, AuthenticationFailed, NotFound, PermissionDenied
from rest_framework.throttling import SimpleRateThrottle

from tenants.models import Business, BusinessDomain, VisitorSession

TOKEN_HEADER = "HTTP_X_VISITOR_TOKEN"


class ChatbotNotFound(NotFound):
    default_code = "chatbot_not_found"
    default_detail = "Chatbot no encontrado."


class OriginNotAllowed(PermissionDenied):
    default_code = "origin_not_allowed"
    default_detail = "Este sitio no está autorizado para usar el chatbot."


class VisitorSessionInvalid(AuthenticationFailed):
    default_code = "visitor_session_invalid"
    default_detail = "La sesión del chat expiró. Se iniciará una nueva."


class SessionLimitReached(APIException):
    status_code = 429
    default_code = "session_message_limit"
    default_detail = "Se alcanzó el límite de mensajes de esta sesión."


def origin_allowed(public_id, origin):
    """¿Puede ``origin`` usar el widget del negocio ``public_id``? Lo usan la vista y el CORS."""
    if not origin:
        return False
    if origin in settings.WIDGET_PREVIEW_ORIGINS:
        return Business.objects.filter(public_id=public_id).exists()
    return BusinessDomain.objects.filter(
        business__public_id=public_id, business__is_active=True, origin=origin
    ).exists()


def widget_business(request, public_id):
    """Negocio activo con chatbot activo, pedido desde un origen autorizado."""
    business = (
        Business.objects.select_related("chatbot")
        .filter(public_id=public_id, is_active=True, chatbot__is_active=True)
        .first()
    )
    if business is None:
        # Inexistente, suspendido o desactivado: la misma respuesta.
        raise ChatbotNotFound()
    origin = request.headers.get("Origin", "")
    if not origin_allowed(public_id, origin):
        raise OriginNotAllowed()
    # Para el log de la petición: el widget actúa en este negocio, sin usuario.
    django_request = getattr(request, "_request", request)
    django_request._tenant = (business, None)
    return business


def visitor_session(request, business):
    token = request.META.get(TOKEN_HEADER, "")
    if not token or len(token) > 100:
        raise VisitorSessionInvalid()
    session = VisitorSession.objects.filter(
        token_hash=VisitorSession.hash(token), business=business
    ).first()
    # Token de otro negocio, revocado o vencido: igual que inexistente.
    if session is None or not session.is_valid:
        raise VisitorSessionInvalid()
    return session


class WidgetSessionThrottle(SimpleRateThrottle):
    """Sesiones nuevas por IP: frena la creación masiva de visitantes."""

    scope = "widget_session"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class WidgetReadThrottle(WidgetSessionThrottle):
    """Lecturas (configuración e historial) por IP."""

    scope = "widget_read"


class WidgetMessageThrottle(SimpleRateThrottle):
    """Mensajes por visitante (su token) y, sin token, por IP."""

    scope = "widget_message"

    def get_cache_key(self, request, view):
        token = request.META.get(TOKEN_HEADER, "")
        ident = VisitorSession.hash(token)[:32] if token else self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class WidgetMessageIpThrottle(WidgetSessionThrottle):
    """Además, un tope por IP: rotar tokens no permite saltarse el límite."""

    scope = "widget_message_ip"


def now():
    return timezone.now()
