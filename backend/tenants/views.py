"""API del panel: el negocio actual (su administrador) y la plataforma (superadministrador).

Todo lo de ``/api/business/...`` actúa sobre el negocio que resolvió el SERVIDOR
(``tenants.context.resolve``): no existe un parámetro para operar sobre otro.
"""
from datetime import timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.models import AuditEvent
from audit.services import record
from chat.models import Conversation, Message
from core.permissions import IsAdminRole, IsPlatformAdmin, IsStaffRole
from faqs.models import FAQ

from .context import resolve
from .models import Business, BusinessDomain, Membership, VisitorSession
from .serializers import (
    AddMemberSerializer,
    BusinessSerializer,
    DomainSerializer,
    MemberSerializer,
    PlatformBusinessSerializer,
)


def _metrics(conversations, messages, faqs):
    since = timezone.now() - timedelta(days=7)
    by_status = dict(conversations.values_list("status").annotate(n=Count("id")).values_list("status", "n"))
    return {
        "conversations_total": sum(by_status.values()),
        "conversations_by_status": {s: by_status.get(s, 0) for s in Conversation.Status.values},
        "conversations_last_7_days": conversations.filter(created_at__gte=since).count(),
        "widget_conversations": conversations.filter(visitor__isnull=False).count(),
        "messages_total": messages.count(),
        "messages_last_7_days": messages.filter(created_at__gte=since).count(),
        "faqs_active": faqs.filter(is_active=True).count(),
        "faqs_total": faqs.count(),
    }


# ---------------------------------------------------------------- negocio actual

class CurrentBusinessView(APIView):
    """GET: equipo del negocio. PATCH: solo su administrador (datos y chatbot)."""

    def get_permissions(self):
        return [IsAdminRole()] if self.request.method != "GET" else [IsStaffRole()]

    def get(self, request):
        business, _ = resolve(request)
        return Response(BusinessSerializer(business).data)

    def patch(self, request):
        business, _ = resolve(request)
        serializer = BusinessSerializer(business, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
        except DjangoValidationError as exc:  # validación del modelo (p. ej. color)
            raise ValidationError({"chatbot": exc.message_dict}) from exc
        action = (
            AuditEvent.Action.CHATBOT_CONFIGURAR if "chatbot" in request.data
            else AuditEvent.Action.NEGOCIO_EDITAR
        )
        record(request, action, detail=f"Negocio {business.id}")
        business.refresh_from_db()
        return Response(BusinessSerializer(business).data)


class DomainListView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        business, _ = resolve(request)
        return Response(DomainSerializer(business.domains.all(), many=True).data)

    def post(self, request):
        business, _ = resolve(request)
        serializer = DomainSerializer(data=request.data, context={"business": business})
        serializer.is_valid(raise_exception=True)
        domain = serializer.save(business=business)
        record(request, AuditEvent.Action.DOMINIO_AGREGAR, detail=domain.origin)
        return Response(DomainSerializer(domain).data, status=status.HTTP_201_CREATED)


class DomainDetailView(APIView):
    permission_classes = [IsAdminRole]

    def delete(self, request, pk):
        business, _ = resolve(request)
        # Un dominio de otro negocio responde 404, igual que uno inexistente.
        domain = get_object_or_404(BusinessDomain, pk=pk, business=business)
        origin = domain.origin
        domain.delete()
        record(request, AuditEvent.Action.DOMINIO_ELIMINAR, detail=origin)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MemberListView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        business, _ = resolve(request)
        members = business.memberships.select_related("user").order_by("role", "user__name")
        return Response(MemberSerializer(members, many=True).data)

    def post(self, request):
        business, _ = resolve(request)
        serializer = AddMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = serializer.save(business)
        record(
            request, AuditEvent.Action.MIEMBRO_AGREGAR,
            detail=f"{membership.user.email} ({membership.role})",
        )
        return Response(MemberSerializer(membership).data, status=status.HTTP_201_CREATED)


class MemberDetailView(APIView):
    permission_classes = [IsAdminRole]

    def delete(self, request, pk):
        business, _ = resolve(request)
        membership = get_object_or_404(Membership, pk=pk, business=business)
        if membership.role == Membership.Role.ADMIN and (
            business.memberships.filter(role=Membership.Role.ADMIN).count() <= 1
        ):
            raise ValidationError({"role": ["El negocio debe conservar al menos un administrador."]})
        email = membership.user.email
        membership.delete()
        record(request, AuditEvent.Action.MIEMBRO_ELIMINAR, detail=email)
        return Response(status=status.HTTP_204_NO_CONTENT)


class BusinessMetricsView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        business, _ = resolve(request)
        conversations = Conversation.objects.filter(business=business)
        messages = Message.objects.filter(conversation__business=business)
        data = _metrics(conversations, messages, business.faqs.all())
        data["team"] = dict(
            business.memberships.values_list("role").annotate(n=Count("id")).values_list("role", "n")
        )
        data["domains"] = business.domains.count()
        return Response(data)


# ---------------------------------------------------------------- plataforma

def _platform_queryset():
    return Business.objects.annotate(
        faq_count=Count("faqs", distinct=True),
        conversation_count=Count("conversations", distinct=True),
    ).prefetch_related("memberships__user")


class PlatformBusinessListView(ListAPIView):
    permission_classes = [IsPlatformAdmin]
    serializer_class = PlatformBusinessSerializer

    def get_queryset(self):
        queryset = _platform_queryset()
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(slug__icontains=search))
        return queryset

    def post(self, request):
        serializer = PlatformBusinessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        business = serializer.save()
        record(
            request, AuditEvent.Action.NEGOCIO_CREAR, detail=f"Negocio {business.id}",
            business=business,
        )
        return Response(
            PlatformBusinessSerializer(_platform_queryset().get(pk=business.pk)).data,
            status=status.HTTP_201_CREATED,
        )


class PlatformBusinessDetailView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request, pk):
        return Response(PlatformBusinessSerializer(get_object_or_404(_platform_queryset(), pk=pk)).data)

    def patch(self, request, pk):
        business = get_object_or_404(Business, pk=pk)
        serializer = PlatformBusinessSerializer(business, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        record(request, AuditEvent.Action.NEGOCIO_EDITAR, detail=f"Negocio {pk}", business=business)
        return Response(PlatformBusinessSerializer(_platform_queryset().get(pk=pk)).data)


class PlatformBusinessStateView(APIView):
    """POST .../suspend/ o .../activate/."""

    permission_classes = [IsPlatformAdmin]
    active = True

    def post(self, request, pk):
        business = get_object_or_404(Business, pk=pk)
        business.is_active = self.active
        business.save(update_fields=["is_active", "updated_at"])
        record(
            request,
            AuditEvent.Action.NEGOCIO_ACTIVAR if self.active else AuditEvent.Action.NEGOCIO_SUSPENDER,
            detail=f"Negocio {pk}",
            business=business,
        )
        return Response(PlatformBusinessSerializer(_platform_queryset().get(pk=pk)).data)


class PlatformBusinessAdminView(APIView):
    """Asigna (o crea) el administrador de un negocio."""

    permission_classes = [IsPlatformAdmin]

    def post(self, request, pk):
        business = get_object_or_404(Business, pk=pk)
        serializer = AddMemberSerializer(data={**request.data, "role": Membership.Role.ADMIN})
        serializer.is_valid(raise_exception=True)
        membership = serializer.save(business)
        record(
            request, AuditEvent.Action.MIEMBRO_AGREGAR,
            detail=f"{membership.user.email} (admin)", business=business,
        )
        return Response(MemberSerializer(membership).data, status=status.HTTP_201_CREATED)


class PlatformMetricsView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        data = _metrics(Conversation.objects.all(), Message.objects.all(), FAQ.objects.all())
        data["businesses_total"] = Business.objects.count()
        data["businesses_active"] = Business.objects.filter(is_active=True).count()
        data["visitor_sessions_24h"] = VisitorSession.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=24)
        ).count()
        return Response(data)
