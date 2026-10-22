from rest_framework import viewsets

from core.permissions import IsAdminOrReadOnly

from .models import FAQ
from .serializers import FAQSerializer


class FAQViewSet(viewsets.ModelViewSet):
    serializer_class = FAQSerializer
    permission_classes = [IsAdminOrReadOnly]

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
