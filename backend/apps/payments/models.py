import uuid

from django.db import models
from django.db.models import Q

from apps.providers.models import ProviderProfile
from apps.subscriptions.models import ProviderSubscription, SubscriptionPlan


def generate_merchant_reference():
    return f"BKO-{uuid.uuid4().hex.upper()}"


class PaymentTransaction(models.Model):
    class Purpose(models.TextChoices):
        ACTIVATE = "ACTIVATE", "Activation"
        RENEW = "RENEW", "Renouvellement"

    class Status(models.TextChoices):
        PENDING = "PENDING", "En attente"
        SUCCEEDED = "SUCCEEDED", "Réussi"
        FAILED = "FAILED", "Échoué"
        CANCELLED = "CANCELLED", "Annulé"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        ProviderProfile,
        on_delete=models.PROTECT,
        related_name="payment_transactions",
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="payment_transactions",
    )
    subscription = models.ForeignKey(
        ProviderSubscription,
        on_delete=models.PROTECT,
        related_name="payment_transactions",
        blank=True,
        null=True,
    )
    purpose = models.CharField(max_length=10, choices=Purpose.choices)
    payment_provider = models.CharField(max_length=50)
    merchant_reference = models.CharField(
        max_length=64,
        unique=True,
        default=generate_merchant_reference,
        editable=False,
    )
    provider_transaction_id = models.CharField(
        max_length=128,
        unique=True,
        blank=True,
        null=True,
    )
    checkout_session_id = models.CharField(max_length=40, unique=True, blank=True, null=True)
    checkout_url = models.URLField(max_length=500, blank=True)
    idempotency_key = models.CharField(max_length=64)
    amount_xof = models.PositiveBigIntegerField()
    currency = models.CharField(max_length=3, default="XOF")
    plan_code_snapshot = models.CharField(max_length=50)
    plan_name_snapshot = models.CharField(max_length=120)
    duration_days_snapshot = models.PositiveSmallIntegerField()
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
    )
    confirmed_at = models.DateTimeField(blank=True, null=True)
    fulfilled_at = models.DateTimeField(blank=True, null=True)
    fulfillment_error_code = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "idempotency_key"],
                name="payments_unique_provider_idempotency",
            ),
            models.CheckConstraint(
                condition=Q(currency="XOF"),
                name="payments_currency_xof_only",
            ),
        ]
        indexes = [
            models.Index(
                fields=["provider", "status", "-created_at"],
                name="payments_provider_status_idx",
            ),
        ]
        permissions = [
            ("manage_payments", "Peut consulter et gérer les paiements"),
        ]

    def __str__(self):
        return f"{self.merchant_reference} — {self.status}"


class PaymentWebhookEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction = models.ForeignKey(
        PaymentTransaction,
        on_delete=models.PROTECT,
        related_name="webhook_events",
    )
    event_fingerprint = models.CharField(max_length=64, unique=True)
    reported_status = models.CharField(max_length=12)
    provider_transaction_id = models.CharField(max_length=128)
    amount_xof = models.PositiveBigIntegerField()
    currency = models.CharField(max_length=3)
    accepted = models.BooleanField(default=False)
    error_code = models.CharField(max_length=64, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["received_at", "id"]

    def __str__(self):
        return f"{self.transaction_id} — {self.reported_status}"
