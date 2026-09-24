from django.urls import path

from .views import (
    AdminPaymentDetailView,
    AdminPaymentListView,
    AdminRetryFulfillmentView,
    PaymentDetailView,
    PaymentListCreateView,
    PaymentWebhookView,
)

urlpatterns = [
    path("transactions/", PaymentListCreateView.as_view(), name="payments"),
    path(
        "transactions/<uuid:pk>/",
        PaymentDetailView.as_view(),
        name="payment-detail",
    ),
    path(
        "webhooks/provider/",
        PaymentWebhookView.as_view(),
        name="payment-webhook",
    ),
    path(
        "admin/transactions/",
        AdminPaymentListView.as_view(),
        name="payment-admin-list",
    ),
    path(
        "admin/transactions/<uuid:pk>/",
        AdminPaymentDetailView.as_view(),
        name="payment-admin-detail",
    ),
    path(
        "admin/transactions/<uuid:pk>/retry-fulfillment/",
        AdminRetryFulfillmentView.as_view(),
        name="payment-admin-retry-fulfillment",
    ),
]
