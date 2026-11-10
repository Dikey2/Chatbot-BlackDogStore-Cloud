"""Permisos por rol DENTRO del negocio resuelto por el servidor (tenants.context).

La autoridad es la membresía del usuario en ese negocio, nunca un dato que
envíe el navegador ni el campo heredado ``User.role``.
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission

from tenants.context import current_role, is_platform_admin

STAFF_ROLES = ("asesor", "admin")


class IsStaffRole(BasePermission):
    """Asesor o administrador del negocio (RF-08, RF-09)."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and current_role(request) in STAFF_ROLES


class IsAdminOrReadOnly(BasePermission):
    """Lectura pública; escritura solo para el administrador del negocio (RF-07, RF-08)."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_authenticated and current_role(request) == "admin"


class IsAdminRole(BasePermission):
    """Administrador del negocio (supervisión, RF-12)."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and current_role(request) == "admin"


class IsPlatformAdmin(BasePermission):
    """Superadministrador de la plataforma."""

    def has_permission(self, request, view):
        return is_platform_admin(request.user)
