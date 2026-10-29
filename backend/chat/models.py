from django.conf import settings
from django.db import models


class Conversation(models.Model):
    class Status(models.TextChoices):
        ABIERTA = "abierta", "Abierta"
        DERIVADA = "derivada", "Derivada a asesor"
        CERRADA = "cerrada", "Cerrada"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations"
    )
    status = models.CharField(
        "estado", max_length=10, choices=Status.choices, default=Status.ABIERTA
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            # Bandeja del asesor: WHERE status = ... ORDER BY created_at DESC.
            models.Index(fields=["status", "-created_at", "-id"], name="conv_estado_fecha_idx"),
            # Historial propio y "latest": WHERE user_id = ... ORDER BY created_at DESC.
            models.Index(fields=["user", "-created_at", "-id"], name="conv_usuario_fecha_idx"),
        ]


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
