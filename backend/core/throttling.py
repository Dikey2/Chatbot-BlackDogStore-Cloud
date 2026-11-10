"""Rate limits con un contador atómico en PostgreSQL.

Antes los límites usaban los throttles de DRF sobre la caché en base de datos:
por cada límite y petición, 4 consultas (leer, contar filas para la limpieza,
buscar y reescribir) y la lista completa de marcas de tiempo de la ventana,
serializada con pickle (decenas de KB con mucho tráfico). Medido en la prueba
de carga del 100 %: era la mayor parte del trabajo de cada petición.

Ahora cada límite cuesta UNA consulta: un UPSERT que suma 1 y devuelve el
contador. La ventana empieza con la primera petición de cada clave (no con el
reloj), así N peticiones dentro de la ventana pasan y la N+1 recibe 429 con
``Retry-After``. Sigue siendo compartido entre todos los procesos de gunicorn.
"""
import random
from datetime import timedelta

from django.db import connection
from django.utils import timezone
from rest_framework import throttling

from .models import RateCounter

# Texto fijo (sin formato): los valores viajan como parámetros del driver.
_UPSERT = """
INSERT INTO core_ratecounter (key, window_start, count)
VALUES (%(key)s, %(now)s, 1)
ON CONFLICT (key) DO UPDATE SET
    count = CASE WHEN core_ratecounter.window_start <= %(expired)s
                 THEN 1 ELSE core_ratecounter.count + 1 END,
    window_start = CASE WHEN core_ratecounter.window_start <= %(expired)s
                        THEN %(now)s ELSE core_ratecounter.window_start END
RETURNING count, window_start
"""

# De vez en cuando se borran contadores viejos para que la tabla no crezca.
CLEANUP_PROBABILITY = 0.001
CLEANUP_AFTER = timedelta(days=1)


def hit(key, duration):
    """Suma una petición a ``key`` y devuelve (contador, inicio de la ventana)."""
    now = timezone.now()
    with connection.cursor() as cursor:
        cursor.execute(
            _UPSERT, {"key": key[:200], "now": now, "expired": now - timedelta(seconds=duration)}
        )
        count, window_start = cursor.fetchone()
    if random.random() < CLEANUP_PROBABILITY:
        RateCounter.objects.filter(window_start__lt=now - CLEANUP_AFTER).delete()
    return count, window_start


class CounterThrottleMixin:
    """Reemplaza el historial de DRF por el contador atómico. Misma API y mismo 429."""

    def allow_request(self, request, view):
        if self.rate is None:
            return True
        self.key = self.get_cache_key(request, view)
        if self.key is None:
            return True
        self.count, self.window_start = hit(self.key, self.duration)
        self.now = timezone.now()
        return self.count <= self.num_requests

    def wait(self):
        remaining = (self.window_start + timedelta(seconds=self.duration) - self.now).total_seconds()
        return max(1, remaining)


class AnonRateThrottle(CounterThrottleMixin, throttling.AnonRateThrottle):
    pass


class UserRateThrottle(CounterThrottleMixin, throttling.UserRateThrottle):
    pass


class ScopedRateThrottle(CounterThrottleMixin, throttling.ScopedRateThrottle):
    def allow_request(self, request, view):
        # ScopedRateThrottle decide su límite según la vista; luego, el contador.
        self.scope = getattr(view, self.scope_attr, None)
        if not self.scope:
            return True
        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)
        return super().allow_request(request, view)


class SimpleRateThrottle(CounterThrottleMixin, throttling.SimpleRateThrottle):
    pass
