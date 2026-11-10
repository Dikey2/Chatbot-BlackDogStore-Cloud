"""Asigna al negocio piloto los registros anteriores a la plataforma multiempresa."""
from django.conf import settings
from django.db import migrations


def forwards(apps, schema_editor):
    Business = apps.get_model("tenants", "Business")
    Model = apps.get_model("chat", "Conversation")
    business = Business.objects.get(slug=settings.DEFAULT_BUSINESS_SLUG)
    Model.objects.filter(business__isnull=True).update(business=business)


class Migration(migrations.Migration):
    dependencies = [
        ("chat", "0003_conversation_assigned_to_conversation_business_and_more"),
        ("tenants", "0002_negocio_piloto"),
    ]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
