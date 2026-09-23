from django.urls import path

from .views import (
    AdminComplaintDetailView,
    AdminComplaintListView,
    AdminComplaintTransitionView,
    ComplaintDetailView,
    ComplaintListCreateView,
)

urlpatterns = [
    path("", ComplaintListCreateView.as_view(), name="complaints"),
    path("admin/", AdminComplaintListView.as_view(), name="complaints-admin"),
    path("admin/<uuid:pk>/", AdminComplaintDetailView.as_view(), name="complaints-admin-detail"),
    path(
        "admin/<uuid:pk>/transition/",
        AdminComplaintTransitionView.as_view(),
        name="complaints-admin-transition",
    ),
    path("<uuid:pk>/", ComplaintDetailView.as_view(), name="complaint-detail"),
]
