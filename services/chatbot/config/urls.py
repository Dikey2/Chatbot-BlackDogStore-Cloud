from django.urls import path

from bot import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("api/reply/", views.reply, name="reply"),
]
