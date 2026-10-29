import logging

from rest_framework.throttling import BaseThrottle

from .models import AuditEvent

logger = logging.getLogger(__name__)
_ident = BaseThrottle()


def record(request, action, result=AuditEvent.Result.EXITO, user=None, email="", detail=""):
    """Guarda un evento. Un fallo al auditar nunca interrumpe la petición."""
    try:
        if user is None and getattr(request, "user", None) is not None:
            if request.user.is_authenticated:
                user = request.user
        AuditEvent.objects.create(
            user=user,
            email=(email or getattr(user, "email", ""))[:254],
            action=action,
            result=result,
            # Misma IP que usa el rate limit (respeta NUM_PROXIES).
            source=_ident.get_ident(request)[:64] if request is not None else "",
            detail=detail[:255],
        )
    except Exception:
        logger.exception("No se pudo registrar el evento de auditoría %s", action)
