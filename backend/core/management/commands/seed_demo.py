"""Carga datos FICTICIOS de demostración: un usuario por rol y FAQ iniciales.

Uso:  python manage.py seed_demo
La contraseña de los tres usuarios sale de la variable de entorno DEMO_PASSWORD.
"""
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from faqs.models import FAQ

USERS = [
    ("admin@example.com", "Admin Demo", "admin"),
    ("asesor@example.com", "Asesor Demo", "asesor"),
    ("cliente@example.com", "Cliente Demo", "cliente"),
]

FAQS = [
    (
        "horarios",
        "¿Cuál es el horario de atención?",
        "DATO FICTICIO: atendemos de lunes a sábado, de 10:00 a 20:00.",
        "horario, horarios, abren, cierran, atienden, atención",
    ),
    (
        "garantias",
        "¿Los productos tienen garantía?",
        "DATO FICTICIO: los productos tienen 12 meses de garantía presentando el comprobante.",
        "garantía, garantías, devolución, devolver, cambio",
    ),
    (
        "servicios",
        "¿Qué servicios técnicos ofrecen?",
        "DATO FICTICIO: ofrecemos mantenimiento y reparación de equipos con diagnóstico previo.",
        "servicio, servicios, reparación, reparan, mantenimiento, técnico",
    ),
]


class Command(BaseCommand):
    help = "Crea usuarios y FAQ ficticios para demostraciones locales."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo solo se ejecuta con DJANGO_DEBUG=true.")
        password = os.environ.get("DEMO_PASSWORD")
        if not password:
            raise CommandError("Definir DEMO_PASSWORD en .env.")

        User = get_user_model()
        for email, name, role in USERS:
            user, _ = User.objects.get_or_create(email=email, defaults={"name": name})
            user.name, user.role = name, role
            user.set_password(password)
            user.save()

        for category, question, answer, keywords in FAQS:
            FAQ.objects.update_or_create(
                question=question,
                defaults={"category": category, "answer": answer, "keywords": keywords},
            )
        self.stdout.write(self.style.SUCCESS(f"{len(USERS)} usuarios y {len(FAQS)} FAQ listos."))
