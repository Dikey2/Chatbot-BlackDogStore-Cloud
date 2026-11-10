"""Compatibilidad hacia atrás: la versión anterior debe poder seguir escribiendo
sobre el esquema nuevo (rollback), y volver a la nueva no deja datos huérfanos."""
import pytest
from django.core.management import call_command

from chat.models import Conversation
from faqs.models import FAQ
from tenants.context import default_business

pytestmark = pytest.mark.django_db


def test_schema_accepts_rows_written_by_the_previous_version(cliente):
    # La versión del 80 % no conoce `business`: inserta sin él.
    faq = FAQ.objects.create(category="c", question="q", answer="a", keywords="k")
    conversation = Conversation.objects.create(user=cliente)
    assert faq.business_id is None and conversation.business_id is None


def test_repair_command_assigns_orphans_to_the_pilot_and_is_idempotent(cliente, capsys):
    FAQ.objects.create(category="c", question="q", answer="a", keywords="k")
    Conversation.objects.create(user=cliente)
    call_command("asignar_negocio_piloto")
    pilot = default_business()
    assert not FAQ.objects.filter(business__isnull=True).exists()
    assert not Conversation.objects.filter(business__isnull=True).exists()
    assert FAQ.objects.get().business == pilot
    call_command("asignar_negocio_piloto")
    assert "0 FAQ, 0 conversaciones" in capsys.readouterr().out


def test_api_always_sets_the_business(admin_api, pilot):
    created = admin_api.post(
        "/api/faqs/", {"category": "c", "question": "q", "answer": "a", "keywords": "k"}, format="json"
    )
    assert FAQ.objects.get(pk=created.json()["id"]).business == pilot
