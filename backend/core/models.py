from django.db import models


class RateCounter(models.Model):
    """Contador de un límite de peticiones (core.throttling). Una fila por clave.

    La ventana empieza con la primera petición de la clave y dura lo que diga
    el límite (p. ej. 60/min). Se actualiza con UNA consulta atómica.
    """

    key = models.CharField(max_length=200, primary_key=True)
    window_start = models.DateTimeField(db_index=True)
    count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "core_ratecounter"
