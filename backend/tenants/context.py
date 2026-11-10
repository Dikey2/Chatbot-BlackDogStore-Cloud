"""Resuelve, en el servidor, en qué negocio actúa cada petición.

- ``X-Business-Id`` (lo envía el panel) SELECCIONA entre los negocios del usuario;
  no autoriza nada. Un negocio al que el usuario no pertenece responde 404, igual
  que uno inexistente, para no confirmar que existe.
- Sin cabecera: el único negocio del usuario, el primero si tiene varios, o el
  negocio por defecto (el piloto) para clientes registrados y visitantes.
- El superadministrador de la plataforma (``is_superuser``) actúa como
  administrador en cualquier negocio.
"""
from django.conf import settings
from rest_framework.exceptions import NotFound, PermissionDenied

from .models import Business, Membership

HEADER = "HTTP_X_BUSINESS_ID"
STAFF_ROLES = (Membership.Role.ADMIN, Membership.Role.ASESOR)


class BusinessSuspended(PermissionDenied):
    default_code = "business_suspended"
    default_detail = "El negocio está suspendido."


def is_platform_admin(user):
    return bool(user and user.is_authenticated and user.is_superuser)


def default_business():
    return Business.objects.filter(slug=settings.DEFAULT_BUSINESS_SLUG).first()


def role_in(user, business):
    """Rol del usuario en el negocio: 'admin', 'asesor' o None."""
    if business is None or not (user and user.is_authenticated):
        return None
    if user.is_superuser:
        return Membership.Role.ADMIN
    return (
        Membership.objects.filter(user=user, business=business)
        .values_list("role", flat=True)
        .first()
    )


def _from_header(request, raw):
    if not str(raw).isdigit():
        raise NotFound("Negocio no encontrado.")
    business = Business.objects.filter(pk=int(raw)).first()
    if business is None or role_in(request.user, business) is None:
        raise NotFound("Negocio no encontrado.")
    return business


def implicit_business(user):
    if user and user.is_authenticated:
        membership = (
            Membership.objects.filter(user=user).select_related("business")
            .order_by("business__name", "business_id").first()
        )
        if membership is not None:
            return membership.business
    return default_business()


def resolve(request):
    """(negocio, rol) de la petición. Se calcula una vez por petición."""
    cached = getattr(request, "_tenant", None)
    if cached is not None:
        return cached
    raw = request.META.get(HEADER)
    user = getattr(request, "user", None)
    if raw and user is not None and user.is_authenticated:
        business = _from_header(request, raw)
    else:
        business = implicit_business(user)
    if business is None:
        raise NotFound("Negocio no encontrado.")
    role = role_in(user, business)
    if not business.is_active and not is_platform_admin(user):
        # Un negocio suspendido no opera: ni su equipo ni sus clientes.
        raise BusinessSuspended()
    request._tenant = (business, role)
    django_request = getattr(request, "_request", None)
    if django_request is not None:
        # Para el log de la petición (core.logging), que ve la petición de Django.
        django_request._tenant = request._tenant
    return request._tenant


def current_business(request):
    return resolve(request)[0]


def current_role(request):
    return resolve(request)[1]
