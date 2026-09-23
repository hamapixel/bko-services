import uuid

from django.conf import settings
from django.db import models

from apps.catalog.models import Trade
from apps.locations.models import Neighborhood


class ProviderProfile(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "En attente"
        VERIFIED = "VERIFIED", "Vérifié"
        REJECTED = "REJECTED", "Refusé"
        SUSPENDED = "SUSPENDED", "Suspendu"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="provider_profile")
    legal_name = models.CharField(max_length=150)
    display_name = models.CharField(max_length=120)
    description = models.CharField(max_length=1000, blank=True)
    trades = models.ManyToManyField(Trade, related_name="providers")
    service_areas = models.ManyToManyField(Neighborhood, related_name="providers")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    is_available = models.BooleanField(default=False)
    identity_checked = models.BooleanField(default=False)
    review_note = models.CharField(max_length=500, blank=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name="verified_providers"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_name", "id"]
        permissions = [("verify_provider", "Peut vérifier les prestataires")]

    def __str__(self):
        return self.display_name


class ProviderReview(models.Model):
    class Decision(models.TextChoices):
        APPROVED = "APPROVED", "Approuvé"
        REJECTED = "REJECTED", "Refusé"
        SUSPENDED = "SUSPENDED", "Suspendu"
        REOPENED = "REOPENED", "Réouvert"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(ProviderProfile, on_delete=models.PROTECT, related_name="reviews")
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    decision = models.CharField(max_length=10, choices=Decision.choices)
    note = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.decision} — {self.profile_id}"
