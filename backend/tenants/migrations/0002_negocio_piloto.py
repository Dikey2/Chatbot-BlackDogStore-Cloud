"""Crea el negocio piloto y da membresía a los administradores y asesores existentes.

Antes de la plataforma multiempresa todo pertenecía a Black Dog Store y la
autoridad era ``User.role``. Desde aquí la autoridad es ``Membership``.
"""
import secrets

from django.conf import settings
from django.db import migrations


def forwards(apps, schema_editor):
    Business = apps.get_model("tenants", "Business")
    ChatbotConfig = apps.get_model("tenants", "ChatbotConfig")
    Membership = apps.get_model("tenants", "Membership")
    User = apps.get_model("users", "User")

    business, _ = Business.objects.get_or_create(
        slug=settings.DEFAULT_BUSINESS_SLUG,
        defaults={
            "name": "Black Dog Store",
            "public_id": "bd_" + secrets.token_urlsafe(12),
            "description": "Negocio piloto de la plataforma (datos ficticios de demostración).",
        },
    )
    ChatbotConfig.objects.get_or_create(
        business=business, defaults={"assistant_name": "Asistente de Black Dog Store"}
    )
    for user in User.objects.filter(role__in=["admin", "asesor"]):
        Membership.objects.get_or_create(
            user=user, business=business, defaults={"role": user.role}
        )


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0001_initial"),
        ("users", "0002_alter_user_managers_remove_user_first_name_and_more"),
    ]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
