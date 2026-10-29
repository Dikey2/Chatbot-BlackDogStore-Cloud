from rest_framework.routers import SimpleRouter

from .views import AuditEventViewSet

router = SimpleRouter()
router.register("audit", AuditEventViewSet, basename="audit")
urlpatterns = router.urls
