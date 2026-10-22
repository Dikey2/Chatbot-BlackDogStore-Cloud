from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

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
            # Mismo mensaje para correo inexistente y contraseña errónea.
            raise AuthenticationFailed("Correo o contraseña incorrectos.")
        token, _ = Token.objects.get_or_create(user=user)
        if is_expired(token):
            # Se reutiliza el token vigente (varias sesiones); uno caducado se reemplaza.
            token.delete()
            token = Token.objects.create(user=user)
        expires_at = token.created + token_ttl()
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
        request.auth.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)
