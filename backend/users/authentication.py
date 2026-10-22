from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed


def token_ttl():
    return timedelta(hours=settings.TOKEN_TTL_HOURS)


def is_expired(token):
    return token.created < timezone.now() - token_ttl()


class ExpiringTokenAuthentication(TokenAuthentication):
    """Token de DRF con caducidad absoluta desde su creación (TOKEN_TTL_HOURS)."""

    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)
        if is_expired(token):
            # Un token caducado no vuelve a servir: se borra.
            token.delete()
            raise AuthenticationFailed(
                "La sesión expiró. Inicie sesión de nuevo.", code="token_expired"
            )
        return user, token
