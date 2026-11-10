"""Carga datos FICTICIOS de demostración para la plataforma multiempresa.

Uso:  python manage.py seed_demo
La contraseña de todas las cuentas sale de la variable de entorno DEMO_PASSWORD.

Crea:
- plataforma@example.com: superadministrador de la plataforma.
- Black Dog Store (negocio piloto): admin@example.com, asesor@example.com, FAQ ficticias.
- Café Aurora (ficticio), segundo negocio independiente: admin@cafe.example.com,
  asesor@cafe.example.com, FAQ propias y otra configuración del chatbot.
- cliente@example.com: cliente registrado del chat de la plataforma.

Orígenes autorizados del widget (opcionales, separados por coma):
SEED_PILOT_ORIGINS y SEED_SECOND_ORIGINS.
"""
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from faqs.models import FAQ
from tenants.models import Business, BusinessDomain, ChatbotConfig, Membership

PILOT_FAQS = [
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

SECOND_FAQS = [
    (
        "menu",
        "¿Qué ofrecen en la carta?",
        "DATO FICTICIO: café de especialidad, infusiones y postres caseros.",
        "menu, carta, cafe, postres, ofrecen",
    ),
    (
        "reservas",
        "¿Aceptan reservas?",
        "DATO FICTICIO: aceptamos reservas para grupos de 6 personas o más.",
        "reserva, reservas, reservar, mesa, grupo",
    ),
    (
        "wifi",
        "¿Tienen wifi?",
        "DATO FICTICIO: sí, wifi gratuito para clientes.",
        "wifi, internet, conexion",
    ),
]


def _origins(name, default):
    return [o.strip() for o in os.environ.get(name, default).split(",") if o.strip()]


class Command(BaseCommand):
    help = "Crea negocios, usuarios y FAQ ficticios para demostraciones locales."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo solo se ejecuta con DJANGO_DEBUG=true.")
        password = os.environ.get("DEMO_PASSWORD")
        if not password:
            raise CommandError("Definir DEMO_PASSWORD en .env.")

        pilot = Business.objects.get(slug=settings.DEFAULT_BUSINESS_SLUG)
        ChatbotConfig.objects.get_or_create(
            business=pilot, defaults={"assistant_name": "Asistente de Black Dog Store"}
        )
        second, _ = Business.objects.get_or_create(
            slug="cafe-aurora",
            defaults={
                "name": "Café Aurora (ficticio)",
                "description": "Segundo negocio de demostración. Todos sus datos son ficticios.",
            },
        )
        ChatbotConfig.objects.update_or_create(
            business=second,
            defaults={
                "assistant_name": "Aurora",
                "welcome_message": "¡Hola! Soy Aurora, del Café Aurora (ficticio). ¿Qué te gustaría saber?",
                "primary_color": "#7c2d12",
                "schedule": "DATO FICTICIO: todos los días de 8:00 a 21:00.",
                "handoff_keywords": "asesor, humano, persona, encargado",
            },
        )

        self._user("plataforma@example.com", "Superadministrador Demo", password, superuser=True)
        self._user("cliente@example.com", "Cliente Demo", password)
        for email, name, role, business in [
            ("admin@example.com", "Admin Demo", "admin", pilot),
            ("asesor@example.com", "Asesor Demo", "asesor", pilot),
            ("admin@cafe.example.com", "Admin Café Demo", "admin", second),
            ("asesor@cafe.example.com", "Asesor Café Demo", "asesor", second),
        ]:
            user = self._user(email, name, password, role=role)
            Membership.objects.update_or_create(user=user, business=business, defaults={"role": role})

        for business, faqs in ((pilot, PILOT_FAQS), (second, SECOND_FAQS)):
            for category, question, answer, keywords in faqs:
                FAQ.objects.update_or_create(
                    business=business,
                    question=question,
                    defaults={"category": category, "answer": answer, "keywords": keywords},
                )

        for business, env, default in (
            (pilot, "SEED_PILOT_ORIGINS", "http://localhost:3002,http://127.0.0.1:3002"),
            (second, "SEED_SECOND_ORIGINS", "http://localhost:8090,http://127.0.0.1:8090"),
        ):
            for origin in _origins(env, default):
                BusinessDomain.objects.get_or_create(business=business, origin=origin)

        for business in (pilot, second):
            self.stdout.write(f"{business.name}: data-chatbot-id=\"{business.public_id}\"")
        self.stdout.write(self.style.SUCCESS("Datos de demostración listos."))

    @staticmethod
    def _user(email, name, password, role="cliente", superuser=False):
        User = get_user_model()
        user, _ = User.objects.get_or_create(email=email, defaults={"name": name})
        user.name = name
        user.role = "admin" if superuser else role
        user.is_superuser = user.is_staff = superuser
        user.set_password(password)
        user.save()
        return user
