from django.contrib import admin
from django.urls import include, path, re_path

from core.errors import api_not_found

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
    path("api/", include("users.urls")),
    path("api/", include("faqs.urls")),
    path("api/", include("chat.urls")),
    path("api/", include("audit.urls")),
    # Cualquier otra ruta bajo /api/ responde 404 en JSON, también con DEBUG activo.
    re_path(r"^api/", api_not_found),
]
