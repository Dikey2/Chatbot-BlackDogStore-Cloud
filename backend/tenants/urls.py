from django.urls import path

from . import views

urlpatterns = [
    path("business/", views.CurrentBusinessView.as_view(), name="business-current"),
    path("business/domains/", views.DomainListView.as_view(), name="business-domains"),
    path("business/domains/<int:pk>/", views.DomainDetailView.as_view(), name="business-domain"),
    path("business/members/", views.MemberListView.as_view(), name="business-members"),
    path("business/members/<int:pk>/", views.MemberDetailView.as_view(), name="business-member"),
    path("business/metrics/", views.BusinessMetricsView.as_view(), name="business-metrics"),
    path("platform/businesses/", views.PlatformBusinessListView.as_view(), name="platform-businesses"),
    path(
        "platform/businesses/<int:pk>/",
        views.PlatformBusinessDetailView.as_view(),
        name="platform-business",
    ),
    path(
        "platform/businesses/<int:pk>/suspend/",
        views.PlatformBusinessStateView.as_view(active=False),
        name="platform-business-suspend",
    ),
    path(
        "platform/businesses/<int:pk>/activate/",
        views.PlatformBusinessStateView.as_view(active=True),
        name="platform-business-activate",
    ),
    path(
        "platform/businesses/<int:pk>/admins/",
        views.PlatformBusinessAdminView.as_view(),
        name="platform-business-admins",
    ),
    path("platform/metrics/", views.PlatformMetricsView.as_view(), name="platform-metrics"),
]
