from django.urls import path

from . import views

urlpatterns = [
    path("widget/<str:public_id>/config/", views.WidgetConfigView.as_view(), name="widget-config"),
    path("widget/<str:public_id>/session/", views.WidgetSessionView.as_view(), name="widget-session"),
    path(
        "widget/<str:public_id>/session/rotate/",
        views.WidgetRotateView.as_view(),
        name="widget-session-rotate",
    ),
    path(
        "widget/<str:public_id>/conversation/",
        views.WidgetConversationView.as_view(),
        name="widget-conversation",
    ),
    path("widget/<str:public_id>/messages/", views.WidgetMessageView.as_view(), name="widget-messages"),
    path("widget/<str:public_id>/handoff/", views.WidgetHandoffView.as_view(), name="widget-handoff"),
]
