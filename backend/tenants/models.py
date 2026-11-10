"""Plataforma multiempresa: cada negocio tiene sus datos, su chatbot y su equipo.

Regla: los datos de un negocio nunca aparecen en otro. Toda consulta de FAQ,
conversaciones y auditoría se filtra por el negocio que el SERVIDOR resolvió
(``tenants.context``); un identificador enviado por el navegador solo selecciona
entre los negocios a los que el usuario ya pertenece.
"""
import hashlib
import secrets
from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

HEX_COLOR = RegexValidator(r"^#[0-9A-Fa-f]{6}$", "Use un color hexadecimal #RRGGBB.")


def new_public_id():
    """Identificador público del widget. No es un secreto: solo dice qué negocio es."""
    return "bd_" + secrets.token_urlsafe(12)


def normalize_origin(value):
    """``https://Tienda.com/ruta`` -> ``https://tienda.com``. Solo http(s), sin ruta ni credenciales."""
    raw = (value or "").strip()
    parts = urlsplit(raw)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValidationError("Indique un origen http(s)://dominio[:puerto].")
    if parts.username or parts.password:
        raise ValidationError("El origen no puede incluir usuario ni contraseña.")
    if "*" in raw:
        raise ValidationError("No se admiten comodines.")
    host = parts.hostname.lower()
    port = f":{parts.port}" if parts.port else ""
    return f"{parts.scheme}://{host}{port}"


class Business(models.Model):
    public_id = models.CharField(
        "identificador público", max_length=40, unique=True, default=new_public_id, editable=False
    )
    slug = models.SlugField("slug", max_length=60, unique=True)
    name = models.CharField("nombre comercial", max_length=120)
    description = models.TextField("descripción", max_length=1000, blank=True)
    logo_url = models.URLField("logotipo", max_length=500, blank=True)
    # Suspendido: el widget deja de responder y su equipo no opera.
    is_active = models.BooleanField("activo", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        verbose_name = "negocio"

    def __str__(self):
        return self.name


class BusinessDomain(models.Model):
    """Origen web autorizado para cargar el widget de un negocio (CORS dinámico)."""

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="domains")
    origin = models.CharField("origen", max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["origin", "id"]
        constraints = [
            models.UniqueConstraint(fields=["business", "origin"], name="dominio_unico_por_negocio"),
        ]
        indexes = [models.Index(fields=["origin"], name="dominio_origen_idx")]

    def save(self, *args, **kwargs):
        self.origin = normalize_origin(self.origin)
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.origin


class Membership(models.Model):
    """Quién trabaja en qué negocio y con qué rol. Es la ÚNICA fuente de autoridad."""

    class Role(models.TextChoices):
        ADMIN = "admin", "Administrador del negocio"
        ASESOR = "asesor", "Asesor"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField("rol", max_length=10, choices=Role.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["business_id", "role", "id"]
        constraints = [
            models.UniqueConstraint(fields=["user", "business"], name="membresia_unica"),
        ]


class ChatbotConfig(models.Model):
    """Lo que cada negocio decide sobre su asistente. Vacío = el bot no lo menciona."""

    business = models.OneToOneField(
        Business, on_delete=models.CASCADE, primary_key=True, related_name="chatbot"
    )
    assistant_name = models.CharField("nombre del asistente", max_length=80, default="Asistente virtual")
    welcome_message = models.CharField(
        "mensaje de bienvenida", max_length=300, default="¡Hola! ¿En qué puedo ayudarte?"
    )
    no_answer_message = models.CharField(
        "mensaje sin respuesta",
        max_length=300,
        default=(
            "No tengo información confirmada sobre esa consulta. "
            "La derivaré a un asesor para su revisión."
        ),
    )
    handoff_message = models.CharField(
        "mensaje de derivación",
        max_length=300,
        default="Listo. Un asesor revisará tu consulta y te responderá por este chat.",
    )
    # Reglas de derivación: si el mensaje contiene una de estas palabras, se deriva.
    handoff_keywords = models.CharField(
        "palabras de derivación", max_length=255, blank=True, default="asesor, humano, persona, agente"
    )
    schedule = models.TextField("horario de atención", max_length=500, blank=True)
    contact_info = models.TextField("información de contacto", max_length=500, blank=True)
    primary_color = models.CharField(
        "color principal", max_length=7, default="#111111", validators=[HEX_COLOR]
    )
    is_active = models.BooleanField("chatbot activo", default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def handoff_keyword_list(self):
        return [k.strip() for k in self.handoff_keywords.split(",") if k.strip()]


class VisitorSession(models.Model):
    """Sesión anónima del widget. En la base solo vive el hash del token."""

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="visitor_sessions")
    token_hash = models.CharField(max_length=64, unique=True)
    origin = models.CharField(max_length=255, blank=True)
    message_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(db_index=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    @staticmethod
    def hash(token):
        return hashlib.sha256(token.encode()).hexdigest()

    @classmethod
    def issue(cls, business, origin=""):
        """Crea una sesión y devuelve (sesión, token). El token en claro no se guarda."""
        token = secrets.token_urlsafe(32)
        session = cls.objects.create(
            business=business,
            token_hash=cls.hash(token),
            origin=origin[:255],
            expires_at=timezone.now() + settings.WIDGET_SESSION_TTL,
        )
        return session, token

    def rotate(self):
        """Token nuevo para la misma sesión; el anterior deja de servir al instante."""
        token = secrets.token_urlsafe(32)
        self.token_hash = self.hash(token)
        self.expires_at = timezone.now() + settings.WIDGET_SESSION_TTL
        self.save(update_fields=["token_hash", "expires_at", "last_seen_at"])
        return token

    @property
    def is_valid(self):
        return self.revoked_at is None and self.expires_at > timezone.now()
