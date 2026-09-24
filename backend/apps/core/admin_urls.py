from django.urls import path

from .admin_views import (
    AdminOverviewView,
    AdminProviderDetailView,
    AdminProviderListView,
    AdminProviderReviewView,
    AdminRequestDetailView,
    AdminRequestDispatchView,
    AdminRequestListView,
    AdminUserDetailView,
    AdminUserListView,
)

urlpatterns = [
    path("overview/", AdminOverviewView.as_view(), name="admin-overview"),
    path("users/", AdminUserListView.as_view(), name="admin-users"),
    path("users/<uuid:pk>/", AdminUserDetailView.as_view(), name="admin-user-detail"),
    path("providers/", AdminProviderListView.as_view(), name="admin-providers"),
    path("providers/<uuid:pk>/", AdminProviderDetailView.as_view(), name="admin-provider-detail"),
    path("providers/<uuid:pk>/review/", AdminProviderReviewView.as_view(), name="admin-provider-review"),
    path("requests/", AdminRequestListView.as_view(), name="admin-requests"),
    path("requests/<uuid:pk>/", AdminRequestDetailView.as_view(), name="admin-request-detail"),
    path("requests/<uuid:pk>/dispatch/", AdminRequestDispatchView.as_view(), name="admin-request-dispatch"),
]
