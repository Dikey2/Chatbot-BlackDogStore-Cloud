from rest_framework import filters, viewsets

from audit.models import AuditEvent
from audit.services import record
from core.permissions import IsAdminOrReadOnly

from .models import FAQ
from .serializers import FAQSerializer


class FAQViewSet(viewsets.ModelViewSet):
    serializer_class = FAQSerializer
    permission_classes = [IsAdminOrReadOnly]
    # ?search=texto busca en pregunta, respuesta y palabras clave.
    # ?ordering=category | -updated_at | question ...
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["question", "answer", "keywords"]
    ordering_fields = ["category", "question", "updated_at", "id"]

    def get_queryset(self):
        queryset = FAQ.objects.all()
        user = self.request.user
        # Solo el administrador ve las FAQ inactivas.
        if not (user.is_authenticated and user.role == "admin"):
            queryset = queryset.filter(is_active=True)
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category=category)
        return queryset

    def perform_create(self, serializer):
        faq = serializer.save()
        record(self.request, AuditEvent.Action.FAQ_CREAR, detail=f"FAQ {faq.id}")

    def perform_update(self, serializer):
        faq = serializer.save()
        record(self.request, AuditEvent.Action.FAQ_EDITAR, detail=f"FAQ {faq.id}")

    def perform_destroy(self, instance):
        faq_id = instance.id
        instance.delete()
        record(self.request, AuditEvent.Action.FAQ_ELIMINAR, detail=f"FAQ {faq_id}")
