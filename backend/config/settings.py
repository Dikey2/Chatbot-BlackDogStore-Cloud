
"""Configuración de la API principal.
Todo valor sensible viene de variables de entorno.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env_list(name, default=""):
    return [
        v.strip()
        for v in os.environ.get(name, default).split(",")
        if v.strip()
    ]


# ==========================================================
# CONFIGURACIÓN GENERAL DE DJANGO
# ==========================================================

# La aplicación no arranca si falta la clave secreta.
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

DEBUG = os.environ.get(
    "DJANGO_DEBUG", "false"
).lower() == "true"

ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS",
    "localhost,127.0.0.1"
)


# ==========================================================
# APLICACIONES INSTALADAS
# ==========================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "rest_framework.authtoken",

    "users",
    "core",
    "faqs",
    "chat",
    "audit",
]


# ==========================================================
# MIDDLEWARE
# ==========================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # CORS con lista explícita de orígenes (core/middleware.py).
    "core.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ==========================================================
# CONFIGURACIÓN PRINCIPAL
# ==========================================================

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# ==========================================================
# BASE DE DATOS POSTGRESQL
# COMPATIBLE CON DOCKER LOCAL Y NEON CLOUD
# ==========================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",

        "NAME": os.environ["POSTGRES_DB"],

        "USER": os.environ["POSTGRES_USER"],

        "PASSWORD": os.environ["POSTGRES_PASSWORD"],

        # "or": una variable definida pero vacía usa el valor por defecto.
        "HOST": os.environ.get("POSTGRES_HOST") or "db",

        "PORT": os.environ.get("POSTGRES_PORT") or "5432",

        # Reutiliza la conexión entre peticiones del mismo proceso: abrir una
        # conexión nueva (y con SSL hacia Neon) en cada petición es costoso.
        "CONN_MAX_AGE": int(os.environ.get("POSTGRES_CONN_MAX_AGE") or "60"),
        # Descarta una conexión reutilizada que se haya cortado.
        "CONN_HEALTH_CHECKS": True,
    }
}


# ==========================================================
# CONEXIÓN SSL PARA NEON POSTGRESQL
# ==========================================================

# En Docker local no necesitamos habilitar SSL.
# En Render utilizaremos POSTGRES_SSLMODE=require.
# En una configuración más estricta se puede utilizar
# verify-full para verificar la identidad del servidor.

POSTGRES_SSLMODE = os.environ.get(
    "POSTGRES_SSLMODE", ""
)

if POSTGRES_SSLMODE:
    DATABASES["default"]["OPTIONS"] = {
        "sslmode": POSTGRES_SSLMODE
    }


# ==========================================================
# MODELO DE USUARIO
# ==========================================================

AUTH_USER_MODEL = "users.User"


# ==========================================================
# CACHÉ COMPARTIDA EN POSTGRESQL
# ==========================================================

# Guarda los contadores de rate limit para compartirlos
# entre los procesos Gunicorn.

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache",
    }
}


# ==========================================================
# VALIDACIÓN DE CONTRASEÑAS
# ==========================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        )
    },
]


# ==========================================================
# DJANGO REST FRAMEWORK
# ==========================================================

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer"
    ],

    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser"
    ],

    "DEFAULT_AUTHENTICATION_CLASSES": [
        "users.authentication.ExpiringTokenAuthentication"
    ],

    # Se requiere autenticación por defecto.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated"
    ],

    # 20 por página; ?page_size= hasta 100 (core/pagination.py).
    "DEFAULT_PAGINATION_CLASS": (
        "core.pagination.StandardPagination"
    ),

    "PAGE_SIZE": 20,

    # Proxies de confianza delante de la API (Render = 1). Sin definir, DRF usa
    # la cabecera X-Forwarded-For completa, que un cliente puede alterar.
    "NUM_PROXIES": (
        int(os.environ["NUM_PROXIES"]) if os.environ.get("NUM_PROXIES") else None
    ),

    "EXCEPTION_HANDLER": (
        "core.errors.exception_handler"
    ),

    # Límites de peticiones.
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],

    "DEFAULT_THROTTLE_RATES": {
        "anon": os.environ.get(
            "THROTTLE_ANON", "60/min"
        ),

        "user": os.environ.get(
            "THROTTLE_USER", "120/min"
        ),

        "auth": os.environ.get(
            "THROTTLE_AUTH", "10/min"
        ),

        "chat": os.environ.get(
            "THROTTLE_CHAT", "30/min"
        ),
    },
}


# ==========================================================
# CONFIGURACIÓN DE SESIONES
# ==========================================================

# La duración del token debe coincidir con el frontend.

TOKEN_TTL_HOURS = float(
    os.environ.get("TOKEN_TTL_HOURS", "8")
)


# ==========================================================
# MICROSERVICIO DEL CHATBOT
# ==========================================================

# Docker local:
# http://chatbot:8000
#
# En Render se configurará la URL real mediante
# la variable CHATBOT_SERVICE_URL.

CHATBOT_SERVICE_URL = os.environ.get(
    "CHATBOT_SERVICE_URL",
    "http://chatbot:8000"
)


# ==========================================================
# HTTPS EN PRODUCCIÓN
# ==========================================================

# DJANGO_HTTPS=true detrás de un proxy con HTTPS (Render). En local queda en false.
if os.environ.get("DJANGO_HTTPS", "false").lower() == "true":
    # Render termina el HTTPS y avisa con X-Forwarded-Proto.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    # Render atiende /api/health/ por HTTP interno: no se redirige.
    SECURE_REDIRECT_EXEMPT = [r"^api/health/$"]
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SECONDS") or "3600")


# ==========================================================
# CORS
# ==========================================================

# Lista explícita de orígenes que pueden llamar a la API desde un navegador.
# Desarrollo: http://localhost:3000. Producción: la URL HTTPS del frontend.
# El frontend actual llama a la API desde su servidor, no desde el navegador.

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "")

if not DEBUG and any("*" in origin for origin in CORS_ALLOWED_ORIGINS):
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured("CORS_ALLOWED_ORIGINS no admite comodines en producción.")


# ==========================================================
# IDIOMA Y ZONA HORARIA
# ==========================================================

LANGUAGE_CODE = "es"

TIME_ZONE = "America/Lima"

USE_I18N = True

USE_TZ = True


# ==========================================================
# ARCHIVOS ESTÁTICOS
# ==========================================================

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
