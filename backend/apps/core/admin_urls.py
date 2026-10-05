from django.urls import path

from .admin_catalog_views import (
    AdminCategoryDetailView,
    AdminCategoryListCreateView,
    AdminTradeDetailView,
    AdminTradeListCreateView,
)
from .admin_user_actions import AdminUserDeleteView, AdminUserStatusView
from .admin_views import (
    AdminOverviewView,
    AdminProviderDetailView,
    AdminProviderListView,
    AdminProviderReviewView,
    AdminRequestDetailView,
    AdminRequestDispatchView,
    AdminRequestResolveLocationView,
    AdminRequestListView,
    AdminUserDetailView,
    AdminUserListView,
)

urlpatterns = [
    path("overview/", AdminOverviewView.as_view(), name="admin-overview"),
    path("users/", AdminUserListView.as_view(), name="admin-users"),
    path("users/<uuid:pk>/", AdminUserDetailView.as_view(), name="admin-user-detail"),
    path("users/<uuid:pk>/status/", AdminUserStatusView.as_view(), name="admin-user-status"),
    path("users/<uuid:pk>/delete/", AdminUserDeleteView.as_view(), name="admin-user-delete"),
    path("providers/", AdminProviderListView.as_view(), name="admin-providers"),
    path("providers/<uuid:pk>/", AdminProviderDetailView.as_view(), name="admin-provider-detail"),
    path("providers/<uuid:pk>/review/", AdminProviderReviewView.as_view(), name="admin-provider-review"),
    path("requests/", AdminRequestListView.as_view(), name="admin-requests"),
    path("requests/<uuid:pk>/", AdminRequestDetailView.as_view(), name="admin-request-detail"),
    path("requests/<uuid:pk>/dispatch/", AdminRequestDispatchView.as_view(), name="admin-request-dispatch"),
    path("requests/<uuid:pk>/resolve-location/", AdminRequestResolveLocationView.as_view(), name="admin-request-resolve-location"),
    path("catalog/categories/", AdminCategoryListCreateView.as_view(), name="admin-catalog-categories"),
    path("catalog/categories/<uuid:pk>/", AdminCategoryDetailView.as_view(), name="admin-catalog-category-detail"),
    path("catalog/trades/", AdminTradeListCreateView.as_view(), name="admin-catalog-trades"),
    path("catalog/trades/<uuid:pk>/", AdminTradeDetailView.as_view(), name="admin-catalog-trade-detail"),
]
