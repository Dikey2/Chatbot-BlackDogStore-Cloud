from rest_framework.permissions import SAFE_METHODS, BasePermission


STAFF_ROLES = ("asesor", "admin")


class IsStaffRole(BasePermission):
    """Solo asesor y administrador (RF-08, RF-09)."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in STAFF_ROLES


class IsAdminOrReadOnly(BasePermission):
    """Lectura pública; escritura solo para el rol administrador (RF-07, RF-08)."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.role == "admin"
