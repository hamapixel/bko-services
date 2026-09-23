import uuid

from django.conf import settings
from django.db import models

from apps.providers.models import ProviderProfile


class SubscriptionPlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=1000, blank=True)
    price_xof = models.PositiveBigIntegerField(default=0)
    duration_days = models.PositiveSmallIntegerField()
    can_receive_requests = models.BooleanField(default=True)
    can_receive_urgent_requests = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "price_xof", "name", "id"]
        permissions = [
            ("manage_subscriptions", "Peut gérer les plans et abonnements"),
        ]

    def __str__(self):
        return self.name


class ProviderSubscription(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Actif"
        CANCELLED = "CANCELLED", "Annulé"
        EXPIRED = "EXPIRED", "Expiré"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.OneToOneField(
        ProviderProfile,
        on_delete=models.PROTECT,
        related_name="subscription",
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    activated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="subscriptions_activated",
    )
    cancelled_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]

    def __str__(self):
        return f"{self.provider_id} — {self.plan.code}"


class SubscriptionHistory(models.Model):
    class Action(models.TextChoices):
        ACTIVATED = "ACTIVATED", "Activation"
        RENEWED = "RENEWED", "Renouvellement"
        CANCELLED = "CANCELLED", "Annulation"
        EXPIRED = "EXPIRED", "Expiration"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(
        ProviderSubscription,
        on_delete=models.PROTECT,
        related_name="history",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="subscription_actions",
    )
    action = models.CharField(max_length=12, choices=Action.choices)
    plan_code = models.CharField(max_length=50)
    plan_name = models.CharField(max_length=120)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    note = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.subscription_id} — {self.action}"
