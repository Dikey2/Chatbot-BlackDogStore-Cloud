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
# --threads permite atender otra petición mientras se espera al chatbot o a PostgreSQL.
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-4} --threads ${GUNICORN_THREADS:-1} --timeout 30 --graceful-timeout 20 --max-requests 10000 --max-requests-jitter 1000 --access-logfile -"]
