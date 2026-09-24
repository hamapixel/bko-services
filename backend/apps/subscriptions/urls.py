from django.urls import path

from .views import (
    AdminActivateSubscriptionView,
    AdminCancelSubscriptionView,
    AdminPlanDetailView,
    AdminPlanListCreateView,
    AdminProviderSubscriptionView,
    AdminRenewSubscriptionView,
    AdminSubscriptionListView,
    MySubscriptionView,
    PublicPlanListView,
)

urlpatterns = [
    path("plans/", PublicPlanListView.as_view(), name="subscription-plans"),
    path("me/", MySubscriptionView.as_view(), name="my-subscription"),
    path("admin/plans/", AdminPlanListCreateView.as_view(), name="subscription-admin-plans"),
    path(
        "admin/plans/<uuid:pk>/",
        AdminPlanDetailView.as_view(),
        name="subscription-admin-plan-detail",
    ),
    path(
        "admin/subscriptions/",
        AdminSubscriptionListView.as_view(),
        name="subscription-admin-list",
    ),
    path(
        "admin/providers/<uuid:provider_id>/",
        AdminProviderSubscriptionView.as_view(),
        name="subscription-admin-provider",
    ),
    path(
        "admin/providers/<uuid:provider_id>/activate/",
        AdminActivateSubscriptionView.as_view(),
        name="subscription-admin-activate",
    ),
    path(
        "admin/subscriptions/<uuid:pk>/renew/",
        AdminRenewSubscriptionView.as_view(),
        name="subscription-admin-renew",
    ),
    path(
        "admin/subscriptions/<uuid:pk>/cancel/",
        AdminCancelSubscriptionView.as_view(),
        name="subscription-admin-cancel",
    ),
]
