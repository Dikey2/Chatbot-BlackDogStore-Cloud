"""Asigna al negocio piloto los registros anteriores a la plataforma multiempresa."""
from django.conf import settings
from django.db import migrations


def forwards(apps, schema_editor):
    Business = apps.get_model("tenants", "Business")
    Model = apps.get_model("audit", "AuditEvent")
    business = Business.objects.get(slug=settings.DEFAULT_BUSINESS_SLUG)
    Model.objects.filter(business__isnull=True).update(business=business)


class Migration(migrations.Migration):
    dependencies = [
        ("audit", "0002_auditevent_business_alter_auditevent_action_and_more"),
        ("tenants", "0002_negocio_piloto"),
    ]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
