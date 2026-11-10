import logging

from rest_framework.throttling import BaseThrottle

from .models import AuditEvent

logger = logging.getLogger(__name__)
events_logger = logging.getLogger("audit.events")
_ident = BaseThrottle()


def record(
    request, action, result=AuditEvent.Result.EXITO, user=None, email="", detail="", business=None
):
    """Guarda un evento y lo emite como log estructurado. Un fallo al auditar
    nunca interrumpe la petición. Nunca recibe contraseñas, tokens ni mensajes."""
    try:
        if business is None and request is not None:
            # El negocio que ya resolvió la petición, si lo hubo (no se fuerza aquí).
            tenant = getattr(request, "_tenant", None)
            business = tenant[0] if tenant else None
        if user is None and getattr(request, "user", None) is not None:
            if request.user.is_authenticated:
                user = request.user
        if business is None and user is not None:
            # Registro, login, logout: el negocio del propio usuario.
            from tenants.context import implicit_business

            business = implicit_business(user)
        source = _ident.get_ident(request)[:64] if request is not None else ""
        AuditEvent.objects.create(
            business=business,
            user=user,
            email=(email or getattr(user, "email", ""))[:254],
            action=action,
            result=result,
            # Misma IP que usa el rate limit (respeta NUM_PROXIES).
            source=source,
            detail=detail[:255],
        )
        events_logger.info(
            "audit_event",
            extra={
                "operation": f"audit.{action}",
                "result": str(result),
                "user_id": getattr(user, "id", None),
                "business_id": getattr(business, "id", None),
                "detail": detail[:255],
            },
        )
    except Exception:
        logger.exception("No se pudo registrar el evento de auditoría %s", action)
