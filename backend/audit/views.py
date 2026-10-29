from rest_framework import viewsets
from rest_framework.exceptions import ValidationError

from core.permissions import IsAdminRole

from .models import AuditEvent
from .serializers import AuditEventSerializer


class AuditEventViewSet(viewsets.ReadOnlyModelViewSet):
    """Solo lectura y solo administrador: el registro no se edita ni se borra por la API."""

    serializer_class = AuditEventSerializer
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        queryset = AuditEvent.objects.select_related("user")
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
