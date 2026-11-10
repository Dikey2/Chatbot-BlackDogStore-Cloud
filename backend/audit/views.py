from rest_framework import viewsets
from rest_framework.exceptions import ValidationError

from core.permissions import IsAdminRole, IsPlatformAdmin
from tenants.context import resolve

from .models import AuditEvent
from .serializers import AuditEventSerializer, PlatformAuditEventSerializer


class AuditEventViewSet(viewsets.ReadOnlyModelViewSet):
    """Solo lectura y solo administrador: el registro no se edita ni se borra por la API."""

    serializer_class = AuditEventSerializer
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        # Solo los eventos del negocio del administrador.
        queryset = AuditEvent.objects.filter(business=resolve(self.request)[0]).select_related("user")
        params = self.request.query_params
        action = params.get("action")
        if action:
            if action not in AuditEvent.Action.values:
                raise ValidationError({"action": ["Acción desconocida."]})
            queryset = queryset.filter(action=action)
        result = params.get("result")
        if result:
            if result not in AuditEvent.Result.values:
                raise ValidationError({"result": ["Resultado desconocido."]})
            queryset = queryset.filter(result=result)
        return queryset


class PlatformAuditEventViewSet(viewsets.ReadOnlyModelViewSet):
    """Auditoría de toda la plataforma, solo superadministrador.

    ?business=<id> filtra un negocio; ?business=none muestra los eventos sin
    negocio (por ejemplo, login fallido de un correo desconocido).
    """

    serializer_class = PlatformAuditEventSerializer
    permission_classes = [IsPlatformAdmin]

    def get_queryset(self):
        queryset = AuditEvent.objects.select_related("user", "business")
        params = self.request.query_params
        business = params.get("business")
        if business == "none":
            queryset = queryset.filter(business__isnull=True)
        elif business:
            if not business.isdigit():
                raise ValidationError({"business": ["Negocio inválido."]})
            queryset = queryset.filter(business_id=int(business))
        action = params.get("action")
        if action:
            if action not in AuditEvent.Action.values:
                raise ValidationError({"action": ["Acción desconocida."]})
            queryset = queryset.filter(action=action)
        result = params.get("result")
        if result:
            if result not in AuditEvent.Result.values:
                raise ValidationError({"result": ["Resultado desconocido."]})
            queryset = queryset.filter(result=result)
        return queryset
