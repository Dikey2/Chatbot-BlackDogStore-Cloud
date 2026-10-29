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

        if origin not in settings.CORS_ALLOWED_ORIGINS:
            return JsonResponse(
                {"error": {"code": "origin_not_allowed", "message": "Origen no permitido."}},
                status=403,
            )

        if request.method == "OPTIONS" and "Access-Control-Request-Method" in request.headers:
            response = HttpResponse(status=204)
            response["Access-Control-Allow-Methods"] = ALLOWED_METHODS
            response["Access-Control-Allow-Headers"] = ALLOWED_HEADERS
            response["Access-Control-Max-Age"] = PREFLIGHT_MAX_AGE
        else:
            response = self.get_response(request)

        # Sin Access-Control-Allow-Credentials: la API usa el encabezado
        # Authorization, no cookies, así que el navegador no envía credenciales.
        response["Access-Control-Allow-Origin"] = origin
        patch_vary_headers(response, ("Origin",))
        return response

    @staticmethod
    def _same_origin(origin, request):
        try:
            return urlsplit(origin).netloc == request.get_host()
        except Exception:
            return False
