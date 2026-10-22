"""Prueba de carga inicial (entrega del 25 %).

SUPUESTO PROVISIONAL, pendiente de confirmar con el docente: el rango 50–100 se
interpreta como PETICIONES HTTP TOTALES, no como usuarios concurrentes.

La prueba se detiene sola al enviar TOTAL_REQUESTS peticiones (100 por defecto),
repartidas entre USERS usuarios simulados. Solo usa datos ficticios y solo debe
apuntar al entorno local de Docker Compose.
"""
import os
import uuid

from locust import HttpUser, between, task
from locust.exception import StopUser

PASSWORD = "Clave-ficticia-123"
QUESTIONS = ["¿Cuál es el horario de atención?", "¿Tienen garantía?", "¿Cuánto cuesta la laptop X?"]

remaining = int(os.environ.get("TOTAL_REQUESTS", "100"))


class Cliente(HttpUser):
    wait_time = between(0.1, 0.5)

    def take(self):
        """Reserva una petición del presupuesto total; al agotarse termina la prueba."""
        global remaining
        if remaining <= 0:
            self.environment.runner.quit()
            raise StopUser()
        remaining -= 1

    def on_start(self):
        email = f"carga-{uuid.uuid4().hex[:12]}@example.com"
        self.take()
        self.client.post(
            "/api/auth/register/",
            json={"name": "Usuario de Carga", "email": email, "password": PASSWORD},
        )
        self.take()
        response = self.client.post(
            "/api/auth/login/", json={"email": email, "password": PASSWORD}
        )
        self.auth = {"Authorization": f"Token {response.json()['token']}"}
        self.question = 0

    @task(1)
    def health(self):
        self.take()
        self.client.get("/api/health/")

    @task(3)
    def list_faqs(self):
        self.take()
        self.client.get("/api/faqs/")

    @task(1)
    def profile(self):
        self.take()
        self.client.get("/api/users/me/", headers=self.auth)

    @task(3)
    def chat(self):
        self.take()
        self.question += 1
        self.client.post(
            "/api/chat/messages/",
            json={"message": QUESTIONS[self.question % len(QUESTIONS)]},
            headers=self.auth,
        )
