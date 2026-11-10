from django.contrib import admin
from django.urls import include, path, re_path

from core.errors import api_not_found
from widget.views import widget_script

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
    path("api/", include("users.urls")),
    path("api/", include("faqs.urls")),
    path("api/", include("chat.urls")),
    path("api/", include("audit.urls")),
    path("api/", include("tenants.urls")),
    path("api/", include("widget.urls")),
    # Script público que cualquier web autorizada carga con <script src=".../widget.js">.
    path("widget.js", widget_script, name="widget-script"),
    # Cualquier otra ruta bajo /api/ responde 404 en JSON, también con DEBUG activo.
    re_path(r"^api/", api_not_found),
]

handler500 = "core.errors.handler500"
