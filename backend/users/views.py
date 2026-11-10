from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from core.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from audit.models import AuditEvent
from audit.services import record

from .authentication import is_expired, token_ttl
from .serializers import LoginSerializer, RegisterSerializer, UserSerializer


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        record(request, AuditEvent.Action.REGISTRO, user=user)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data["email"].lower(),
            password=serializer.validated_data["password"],
        )
        if user is None:
            record(
                request,
                AuditEvent.Action.LOGIN_FALLIDO,
                AuditEvent.Result.FALLO,
                email=serializer.validated_data["email"].lower(),
            )
            # Mismo mensaje para correo inexistente y contraseña errónea.
            raise AuthenticationFailed("Correo o contraseña incorrectos.")
        token, _ = Token.objects.get_or_create(user=user)
        if is_expired(token):
            # Se reutiliza el token vigente (varias sesiones); uno caducado se reemplaza.
            token.delete()
            token = Token.objects.create(user=user)
        expires_at = token.created + token_ttl()
        record(request, AuditEvent.Action.LOGIN, user=user)
        return Response(
            {
                "token": token.key,
                "expires_at": expires_at.isoformat(),
                "user": UserSerializer(user).data,
            }
        )

    def get_authenticate_header(self, request):
        # Sin esto DRF convierte el 401 en 403 porque la vista no tiene autenticadores.
        return "Token"


class LogoutView(APIView):
    def post(self, request):
        record(request, AuditEvent.Action.LOGOUT)
        request.auth.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    """Perfil, negocios del usuario y su rol EN el negocio resuelto.

    ``role`` es el rol efectivo en ese negocio ('admin', 'asesor' o 'cliente'),
    el que usa el panel para decidir qué mostrar. La API vuelve a comprobarlo
    en cada petición.
    """

    def get(self, request):
        from tenants.context import is_platform_admin, resolve
        from tenants.models import Membership

        user = request.user
        business, role = resolve(request)
        memberships = [
            {
                "business_id": m.business_id,
                "business_name": m.business.name,
                "public_id": m.business.public_id,
                "role": m.role,
                "is_active": m.business.is_active,
            }
            for m in Membership.objects.filter(user=user).select_related("business")
            .order_by("business__name", "business_id")
        ]
        data = UserSerializer(user).data
        data["role"] = role or "cliente"
        data["business"] = {
            "id": business.id,
            "name": business.name,
            "public_id": business.public_id,
        }
        data["memberships"] = memberships
        data["is_platform_admin"] = is_platform_admin(user)
        return Response(data)
