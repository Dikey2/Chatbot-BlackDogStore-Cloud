from django.db import models


class FAQ(models.Model):
    """Pregunta frecuente administrada (RF-04). El chatbot responde con `answer`."""

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

    def __str__(self):
        return self.question

    def keyword_list(self):
        return [k.strip() for k in self.keywords.split(",") if k.strip()]
