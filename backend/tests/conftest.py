import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from faqs.models import FAQ

PASSWORD = "Clave-ficticia-123"


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    # Los contadores de rate limit viven en la caché; cada prueba empieza en cero.
    cache.clear()


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def make_user(db):
    def _make(email="cliente@example.com", role="cliente", name="Persona Ficticia"):
        return get_user_model().objects.create_user(
            email=email, password=PASSWORD, name=name, role=role
        )

    return _make


def client_for(user):
    client = APIClient()
    token = Token.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


@pytest.fixture
def cliente(make_user):
    return make_user()


@pytest.fixture
def cliente_api(cliente):
    return client_for(cliente)


@pytest.fixture
def asesor_api(make_user):
    return client_for(make_user("asesor@example.com", "asesor"))


@pytest.fixture
def admin_api(make_user):
    return client_for(make_user("admin@example.com", "admin"))


@pytest.fixture
def faq(db):
    return FAQ.objects.create(
        category="horarios",
        question="¿Cuál es el horario?",
        answer="DATO FICTICIO: de 10:00 a 20:00.",
        keywords="horario, atención",
    )
