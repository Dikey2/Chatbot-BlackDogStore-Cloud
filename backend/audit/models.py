from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    """Registro inmutable de accesos y operaciones relevantes (RF-12).

    Nunca guarda contraseñas, tokens ni el contenido de los mensajes.
    """

    class Action(models.TextChoices):
        REGISTRO = "registro", "Registro"
        LOGIN = "login", "Inicio de sesión"
        LOGIN_FALLIDO = "login_fallido", "Inicio de sesión fallido"
        LOGOUT = "logout", "Cierre de sesión"
        TOKEN_EXPIRADO = "token_expirado", "Token expirado"
        ACCESO_DENEGADO = "acceso_denegado", "Acceso denegado"
        FAQ_CREAR = "faq_crear", "FAQ creada"
        FAQ_EDITAR = "faq_editar", "FAQ editada"
        FAQ_ELIMINAR = "faq_eliminar", "FAQ eliminada"
        CONVERSACION_RESPONDER = "conversacion_responder", "Respuesta de asesor"
        CONVERSACION_CERRAR = "conversacion_cerrar", "Conversación cerrada"
        CONVERSACION_DERIVAR = "conversacion_derivar", "Conversación derivada"
        CONVERSACION_ASIGNAR = "conversacion_asignar", "Conversación tomada por asesor"
        NEGOCIO_CREAR = "negocio_crear", "Negocio creado"
        NEGOCIO_EDITAR = "negocio_editar", "Negocio editado"
        NEGOCIO_SUSPENDER = "negocio_suspender", "Negocio suspendido"
        NEGOCIO_ACTIVAR = "negocio_activar", "Negocio activado"
        CHATBOT_CONFIGURAR = "chatbot_configurar", "Chatbot configurado"
        DOMINIO_AGREGAR = "dominio_agregar", "Dominio autorizado"
        DOMINIO_ELIMINAR = "dominio_eliminar", "Dominio retirado"
        MIEMBRO_AGREGAR = "miembro_agregar", "Miembro agregado"
        MIEMBRO_ELIMINAR = "miembro_eliminar", "Miembro retirado"

    class Result(models.TextChoices):
        EXITO = "exito", "Éxito"
        FALLO = "fallo", "Fallo"

    # Negocio en el que ocurrió. Vacío = evento de plataforma o sin negocio resuelto.
    business = models.ForeignKey(
        "tenants.Business",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
    )
    # SET_NULL: el registro sobrevive aunque se borre el usuario.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
    )
    email = models.EmailField("correo", blank=True)
    action = models.CharField("acción", max_length=30, choices=Action.choices)
    result = models.CharField("resultado", max_length=10, choices=Result.choices)
    source = models.CharField("origen", max_length=64, blank=True)
    detail = models.CharField("detalle", max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            # Listado del administrador: más recientes primero, con o sin filtro.
            models.Index(fields=["-created_at", "-id"], name="audit_recientes_idx"),
            models.Index(fields=["action", "-created_at"], name="audit_accion_idx"),
            models.Index(fields=["business", "-created_at", "-id"], name="audit_negocio_idx"),
        ]
