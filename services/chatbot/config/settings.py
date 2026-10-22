"""Servicio de chatbot: sin base de datos ni sesiones. Solo reglas y FAQ."""
import os

SECRET_KEY = os.environ["CHATBOT_SECRET_KEY"]
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("CHATBOT_ALLOWED_HOSTS", "localhost,127.0.0.1,chatbot").split(",")
    if h.strip()
]

INSTALLED_APPS = ["rest_framework", "bot"]
MIDDLEWARE = ["django.middleware.common.CommonMiddleware"]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {}

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "UNAUTHENTICATED_USER": None,
}

USE_TZ = True
