"""Pruebas de carga y estrés con Locust. Solo contra Docker Compose local.

Perfiles (se eligen por nombre de clase en la línea de comandos):

- ``Lectura``: cliente de demostración que solo consulta (health, FAQ,
  historial propio, perfil). No escribe en PostgreSQL.
- ``LecturaAsesor``: asesor de demostración que recorre la bandeja paginada.
  No escribe en PostgreSQL.
- ``Escritura``: usuario nuevo y ficticio que se registra, inicia sesión y
  conversa con el chatbot. Escribe usuarios, tokens, conversaciones y mensajes.

Modalidades:

- A (solicitudes totales): ``TOTAL_REQUESTS=1000`` detiene la prueba al
  enviar ese número de peticiones, sin importar cuántos usuarios haya.
- B (usuarios concurrentes): ``TOTAL_REQUESTS=0`` (sin límite) junto con
  ``--users`` y ``--run-time``.

Las cuentas de lectura son las de ``seed_demo``; su contraseña llega por la
variable ``DEMO_PASSWORD`` y nunca se escribe en este archivo ni en los
resultados.
"""
import os
import random
import uuid

from locust import HttpUser, between, events, task
from locust.exception import StopUser

PASSWORD = "Clave-ficticia-123"
QUESTIONS = [
    "¿Cuál es el horario de atención?",
    "¿Tienen garantía?",
    "¿Qué servicios técnicos ofrecen?",
    "¿Cuánto cuesta la laptop X?",
]
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "")
TOTAL = int(os.environ.get("TOTAL_REQUESTS", "0"))
remaining = TOTAL


@events.test_start.add_listener
def _reset_budget(**_):
    global remaining
    remaining = TOTAL


class Base(HttpUser):
    abstract = True
    wait_time = between(0.1, 0.5)

    def take(self):
        """Modalidad A: reserva una petición del total; al agotarse termina la prueba."""
        global remaining
        if TOTAL <= 0:
            return
        if remaining <= 0:
            self.environment.runner.quit()
            raise StopUser()
        remaining -= 1

    def login(self, email, password):
        self.take()
        response = self.client.post(
            "/api/auth/login/", json={"email": email, "password": password}
        )
        if response.status_code != 200:
            # El fallo ya queda contado por Locust; sin sesión el usuario no sigue.
            raise StopUser()
        self.auth = {"Authorization": f"Token {response.json()['token']}"}

    def get(self, path, name=None, auth=True):
        self.take()
        return self.client.get(path, headers=self.auth if auth else None, name=name)


class Lectura(Base):
    """Solo lectura con el cliente de demostración."""

    def on_start(self):
        if not DEMO_PASSWORD:
            raise RuntimeError("Falta DEMO_PASSWORD para las pruebas de lectura.")
        self.login("cliente@example.com", DEMO_PASSWORD)

    @task(1)
    def health(self):
        self.get("/api/health/", auth=False)

    @task(3)
    def faqs(self):
        self.get("/api/faqs/", auth=False)

    @task(2)
    def historial(self):
        self.get("/api/chat/conversations/", name="/api/chat/conversations/ (propias)")

    @task(2)
    def ultima(self):
        self.get("/api/chat/conversations/latest/")

    @task(1)
    def perfil(self):
        self.get("/api/users/me/")


class LecturaAsesor(Base):
    """Solo lectura: bandeja paginada del asesor sobre todas las conversaciones."""

    def on_start(self):
        if not DEMO_PASSWORD:
            raise RuntimeError("Falta DEMO_PASSWORD para las pruebas de lectura.")
        self.login("asesor@example.com", DEMO_PASSWORD)
        # Solo se piden páginas que existen (máximo 5 por estado): una página
        # inexistente responde 404 y mediría un error de la prueba, no del servidor.
        self.pages = {}
        for status in ("derivada", "abierta", "cerrada"):
            count = self.get(
                f"/api/chat/conversations/?status={status}",
                name="/api/chat/conversations/?status=[estado]&page=[n]",
            ).json().get("count", 0)
            if count:
                self.pages[status] = min(5, -(-count // 20))
        if not self.pages:
            raise StopUser()

    @task
    def bandeja(self):
        status = random.choice(list(self.pages))
        page = random.randint(1, self.pages[status])
        self.get(
            f"/api/chat/conversations/?status={status}&page={page}",
            name="/api/chat/conversations/?status=[estado]&page=[n]",
        )


class Escritura(Base):
    """Escribe en PostgreSQL: registro, login y chat con datos ficticios."""

    def on_start(self):
        email = f"carga-{uuid.uuid4().hex[:12]}@example.com"
        self.take()
        self.client.post(
            "/api/auth/register/",
            json={"name": "Usuario de Carga", "email": email, "password": PASSWORD},
        )
        self.login(email, PASSWORD)
        self.conversation = None
        self.turn = 0

    @task(4)
    def chat(self):
        self.take()
        self.turn += 1
        body = {"message": QUESTIONS[self.turn % len(QUESTIONS)]}
        if self.conversation:
            body["conversation_id"] = self.conversation
        response = self.client.post("/api/chat/messages/", json=body, headers=self.auth)
        if response.status_code == 201:
            self.conversation = response.json()["conversation"]["id"]

    @task(1)
    def historial(self):
        self.get("/api/chat/conversations/latest/")

    @task(1)
    def faqs(self):
        self.get("/api/faqs/", auth=False)

    @task(1)
    def health(self):
        self.get("/api/health/", auth=False)
