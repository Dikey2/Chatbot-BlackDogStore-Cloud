FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

COPY . .
RUN useradd --create-home app && chown -R app /app
USER app

EXPOSE 8000
# gunicorn en lugar de runserver: el servidor de desarrollo tiene una cola de 5
# conexiones y no está pensado para carga concurrente (ver docs/PRUEBAS.md).
CMD ["sh", "-c", "exec gunicorn config.wsgi --bind 0.0.0.0:8000 --workers ${CHATBOT_WORKERS:-2} --timeout 10 --access-logfile -"]
