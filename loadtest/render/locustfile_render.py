"""Prueba de carga CONTROLADA contra los servicios publicados en Render.

Autorizada por el propietario el 11 de noviembre de 2026, con estas condiciones:
- Escalonada y pequeña: 100, 1000 y 5000 solicitudes totales.
- Solo lectura: nada escribe en la base de datos ni crea conversaciones.
- Se detiene sola ante errores (ver ``ABORT_*``).

Endpoints (todos sin rate limit, para medir el servidor y no el límite de 60/min):
- ``GET /api/health/live/``: proceso de Django vivo, sin dependencias.
- ``GET /api/health/``: consulta mínima a PostgreSQL (Neon) y al servicio del chatbot.
- ``GET /widget.js``: archivo que descargan los sitios con el widget.
- ``GET /login`` del frontend (Next.js): otro servicio de Render.

Uso: loadtest/render/ejecutar_render.sh <total> <usuarios>
"""
import os

import gevent
from locust import HttpUser, between, events, task
from locust.exception import StopUser

FRONTEND = os.environ.get("FRONTEND_URL", "https://blackdog-chatbot-frontend.onrender.com")
TOTAL = int(os.environ.get("TOTAL_REQUESTS", "100"))
# Se aborta con más de 5 errores, o si más del 2 % de las respuestas (con al menos 50) falla.
ABORT_ERRORS = 5
ABORT_RATE = 0.02

remaining = TOTAL
stats = {"total": 0, "errors": 0}


@events.test_start.add_listener
def _reset(**_):
    global remaining
    remaining = TOTAL
    ENV["stopping"] = False
    stats.update(total=0, errors=0)


@events.request.add_listener
def _watch(request_type, name, response_time, response_length, response=None, exception=None, context=None, **kwargs):
    stats["total"] += 1
    status = getattr(response, "status_code", 0)
    if exception is not None or status >= 500 or status == 0:
        stats["errors"] += 1
    too_many = stats["errors"] > ABORT_ERRORS
    too_high = stats["total"] >= 50 and stats["errors"] / stats["total"] > ABORT_RATE
    if too_many or too_high:
        print(f"ABORTADA: {stats['errors']} errores en {stats['total']} solicitudes")
        stop(ENV["env"].runner)


ENV = {}


def stop(runner):
    """Detiene la prueba desde otro greenlet: llamado desde un usuario, quit() no termina."""
    if not ENV.get("stopping"):
        ENV["stopping"] = True
        gevent.spawn(runner.quit)


@events.init.add_listener
def _keep_env(environment, **_):
    ENV["env"] = environment


class Visitante(HttpUser):
    wait_time = between(0.2, 0.6)

    def take(self):
        global remaining
        if remaining <= 0:
            stop(self.environment.runner)
            raise StopUser()
        remaining -= 1

    @task(3)
    def live(self):
        self.take()
        self.client.get("/api/health/live/", name="API /api/health/live/")

    @task(2)
    def health(self):
        self.take()
        self.client.get("/api/health/", name="API /api/health/ (Neon + chatbot)")

    @task(2)
    def widget(self):
        self.take()
        self.client.get("/widget.js", name="API /widget.js")

    @task(1)
    def login_page(self):
        self.take()
        self.client.get(f"{FRONTEND}/login", name="Frontend /login")
