FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# Imagen de desarrollo: incluye las dependencias de pruebas.
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

COPY . .
RUN useradd --create-home app && chown -R app /app
USER app

EXPOSE 8000
# gunicorn: varios procesos y cola de conexiones amplia. runserver (cola de 5)
# reseteaba conexiones con 50 usuarios concurrentes; ver docs/PRUEBAS.md.
# --max-requests recicla cada proceso tras N peticiones (evita que crezca la memoria).
# --preload carga Django una vez en el proceso maestro: reciclar un proceso es solo
# un fork, no volver a importar todo. Medido en la prueba de 50 000 solicitudes:
# con 10000 sin preload, varios procesos se reciclaban a la vez y el servicio caía
# a ~35 req/s durante ~45 s. La memoria se mantuvo estable (~212 MiB), así que el
# reciclaje se espacia (20000 ± 4000) para que los procesos no coincidan.
# --threads permite atender otra petición mientras se espera al chatbot o a PostgreSQL.
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-4} --threads ${GUNICORN_THREADS:-1} --timeout 30 --graceful-timeout 20 --preload --max-requests 20000 --max-requests-jitter 4000"]
