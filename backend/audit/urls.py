from rest_framework.routers import SimpleRouter

from .views import AuditEventViewSet, PlatformAuditEventViewSet

router = SimpleRouter()
router.register("audit", AuditEventViewSet, basename="audit")
router.register("platform/audit", PlatformAuditEventViewSet, basename="platform-audit")
urlpatterns = router.urls
