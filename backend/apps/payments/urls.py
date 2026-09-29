from django.urls import path

from .views import (
    AdminPaymentDetailView,
    AdminPaymentListView,
    AdminRetryFulfillmentView,
    PaymentDetailView,
    PaymentListCreateView,
    PaymentMethodsView,
    PaymentWebhookView,
    WaveCheckoutView,
    WaveWebhookView,
)

urlpatterns = [
    path("methods/", PaymentMethodsView.as_view(), name="payment-methods"),
    path("wave/checkout/", WaveCheckoutView.as_view(), name="wave-checkout"),
    path("webhooks/wave/", WaveWebhookView.as_view(), name="wave-webhook"),
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
