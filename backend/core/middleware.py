"""CORS con lista explícita de orígenes (CORS_ALLOWED_ORIGINS).

CORS es una política que aplican los navegadores: solo decide si una página de
otro origen puede leer la respuesta. No reemplaza a la autenticación ni a los
permisos, que la API comprueba en cada petición.

Además de no enviar las cabeceras CORS a orígenes desconocidos, este middleware
rechaza con 403 cualquier petición cuyo encabezado ``Origin`` no esté autorizado,
para que un sitio ajeno tampoco pueda provocar escrituras desde el navegador.
Las peticiones sin ``Origin`` (el servidor de Next.js, curl, Locust) no se
ven afectadas.
"""
from urllib.parse import urlsplit

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils.cache import patch_vary_headers

ALLOWED_METHODS = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
ALLOWED_HEADERS = "Authorization, Content-Type"
PREFLIGHT_MAX_AGE = "600"

# Widget público: cada negocio autoriza sus propios orígenes (BusinessDomain).
WIDGET_PREFIX = "/api/widget/"
WIDGET_METHODS = "GET, POST, OPTIONS"
WIDGET_HEADERS = "Content-Type, X-Visitor-Token"


def _widget_public_id(path):
    if not path.startswith(WIDGET_PREFIX):
        return None
    return path[len(WIDGET_PREFIX):].split("/", 1)[0] or None


class CorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.headers.get("Origin")
        if not origin:
            return self.get_response(request)

        if self._same_origin(origin, request):
            # Petición del propio sitio (por ejemplo, el panel /admin/ de Django).
            return self.get_response(request)

        public_id = _widget_public_id(request.path)
        if public_id is not None:
            allowed = self._widget_origin_allowed(public_id, origin, request)
            methods, headers = WIDGET_METHODS, WIDGET_HEADERS
        else:
            allowed = origin in settings.CORS_ALLOWED_ORIGINS
            methods, headers = ALLOWED_METHODS, ALLOWED_HEADERS

        if not allowed:
            return JsonResponse(
                {"error": {"code": "origin_not_allowed", "message": "Origen no permitido."}},
                status=403,
            )

        if request.method == "OPTIONS" and "Access-Control-Request-Method" in request.headers:
            response = HttpResponse(status=204)
            response["Access-Control-Allow-Methods"] = methods
            response["Access-Control-Allow-Headers"] = headers
            response["Access-Control-Max-Age"] = PREFLIGHT_MAX_AGE
        else:
            response = self.get_response(request)

        # Sin Access-Control-Allow-Credentials: la API usa el encabezado
        # Authorization, no cookies, así que el navegador no envía credenciales.
        response["Access-Control-Allow-Origin"] = origin
        patch_vary_headers(response, ("Origin",))
        return response

    @staticmethod
    def _widget_origin_allowed(public_id, origin, request):
        from widget.security import origin_allowed

        try:
            return origin_allowed(public_id, origin, request)
        except Exception:
            # Sin base de datos no se puede comprobar: se rechaza (la vista daría 503).
            return False

    @staticmethod
    def _same_origin(origin, request):
        try:
            return urlsplit(origin).netloc == request.get_host()
        except Exception:
            return False


class DatabaseUnavailableMiddleware:
    """PostgreSQL caído fuera de una vista de DRF (por ejemplo, en otro middleware): 503 JSON."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        from django.db.utils import InterfaceError, OperationalError

        if isinstance(exception, (OperationalError, InterfaceError)):
            response = JsonResponse(
                {
                    "error": {
                        "code": "database_unavailable",
                        "message": "La base de datos no está disponible. Inténtelo más tarde.",
                    }
                },
                status=503,
            )
            response["Retry-After"] = "10"
            return response
        return None
