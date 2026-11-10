from django.conf import settings
from django.db import models


class Conversation(models.Model):
    class Status(models.TextChoices):
        ABIERTA = "abierta", "Abierta"
        DERIVADA = "derivada", "Derivada a asesor"
        ATENDIENDO = "atendiendo", "En atención"
        CERRADA = "cerrada", "Cerrada"

    # null=True solo en la base, por compatibilidad hacia atrás (ver faqs.models.FAQ.business).
    business = models.ForeignKey(
        "tenants.Business", on_delete=models.CASCADE, related_name="conversations", null=True
    )
    # Cliente registrado (chat de la plataforma) o visitante anónimo del widget.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations",
        null=True,
        blank=True,
    )
    visitor = models.ForeignKey(
        "tenants.VisitorSession",
        on_delete=models.SET_NULL,
        related_name="conversations",
        null=True,
        blank=True,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="assigned_conversations",
        null=True,
        blank=True,
    )
    status = models.CharField(
        "estado", max_length=10, choices=Status.choices, default=Status.ABIERTA
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            # Toda conversación es de un cliente registrado o de un visitante del widget.
            models.CheckConstraint(
                condition=models.Q(user__isnull=False) | models.Q(visitor__isnull=False),
                name="conv_tiene_cliente_o_visitante",
            ),
        ]
        indexes = [
            # Bandeja del asesor: WHERE status = ... ORDER BY created_at DESC.
            models.Index(fields=["status", "-created_at", "-id"], name="conv_estado_fecha_idx"),
            # Historial propio y "latest": WHERE user_id = ... ORDER BY created_at DESC.
            models.Index(fields=["user", "-created_at", "-id"], name="conv_usuario_fecha_idx"),
            # Bandeja por negocio: WHERE business_id = ... AND status = ... ORDER BY created_at DESC.
            models.Index(
                fields=["business", "status", "-created_at", "-id"], name="conv_negocio_estado_idx"
            ),
            # Conversación vigente de un visitante del widget.
            models.Index(fields=["visitor", "-created_at", "-id"], name="conv_visitante_idx"),
        ]

    @property
    def client_name(self):
        if self.user_id:
            return self.user.name
        return f"Visitante #{self.visitor_id}" if self.visitor_id else "Visitante"


class Message(models.Model):
    class Sender(models.TextChoices):
        CLIENTE = "cliente", "Cliente"
        BOT = "bot", "Chatbot"
        ASESOR = "asesor", "Asesor"

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.CharField("emisor", max_length=10, choices=Sender.choices)
    content = models.TextField("contenido")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            # Mensajes de una conversación en orden cronológico.
            models.Index(fields=["conversation", "created_at", "id"], name="msg_conv_fecha_idx"),
        ]
