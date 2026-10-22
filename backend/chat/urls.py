from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import ConversationViewSet, SendMessageView

router = SimpleRouter()
router.register("chat/conversations", ConversationViewSet, basename="conversation")

urlpatterns = [
    path("chat/messages/", SendMessageView.as_view(), name="chat-messages"),
    *router.urls,
]
