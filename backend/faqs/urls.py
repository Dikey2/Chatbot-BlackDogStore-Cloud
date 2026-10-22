from rest_framework.routers import SimpleRouter

from .views import FAQViewSet

router = SimpleRouter()
router.register("faqs", FAQViewSet, basename="faq")
urlpatterns = router.urls
