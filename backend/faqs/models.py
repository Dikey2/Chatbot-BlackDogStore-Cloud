from django.db import models


class FAQ(models.Model):
    """Pregunta frecuente administrada (RF-04). El chatbot responde con `answer`.

    Pertenece a UN negocio: el chatbot de un negocio nunca usa FAQ de otro.
    """

    # null=True SOLO en la base (compatibilidad hacia atrás): la versión anterior,
    # que no conoce este campo, puede seguir creando FAQ durante un rollback. La
    # aplicación siempre lo completa y `asignar_negocio_piloto` repara los huérfanos.
    business = models.ForeignKey(
        "tenants.Business", on_delete=models.CASCADE, related_name="faqs", null=True
    )
    category = models.CharField("categoría", max_length=50, db_index=True)
    question = models.CharField("pregunta", max_length=255)
    answer = models.TextField("respuesta")
    keywords = models.CharField(
        "palabras clave",
        max_length=255,
        help_text="Separadas por coma. El chatbot las busca en el mensaje del cliente.",
    )
    is_active = models.BooleanField("activa", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "id"]
        indexes = [
            # FAQ activas de un negocio: lo que lee el chatbot en cada mensaje.
            models.Index(fields=["business", "is_active", "category"], name="faq_negocio_activa_idx"),
        ]

    def __str__(self):
        return self.question

    def keyword_list(self):
        return [k.strip() for k in self.keywords.split(",") if k.strip()]
