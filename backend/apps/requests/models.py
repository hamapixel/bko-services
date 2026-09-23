import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.catalog.models import Trade
from apps.locations.models import Neighborhood


class ServiceRequest(models.Model):
    class Priority(models.TextChoices):
        NORMAL = "NORMAL", "Normale"
        URGENT = "URGENT", "Urgente"

    class Status(models.TextChoices):
        CREATED = "CREATED", "Enregistrée"
        SEARCHING = "SEARCHING", "Recherche en cours"
        OFFERED = "OFFERED", "Proposée"
        ACCEPTED = "ACCEPTED", "Acceptée"
        EN_ROUTE = "EN_ROUTE", "En route"
        ARRIVED = "ARRIVED", "Arrivé"
        IN_PROGRESS = "IN_PROGRESS", "En cours"
        PROVIDER_COMPLETED = "PROVIDER_COMPLETED", "Terminée par le prestataire"
        CLIENT_CONFIRMED = "CLIENT_CONFIRMED", "Confirmée par le client"
        CANCELLED = "CANCELLED", "Annulée"
        DISPUTED = "DISPUTED", "Contestée"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="service_requests")
    trade = models.ForeignKey(Trade, on_delete=models.PROTECT, related_name="service_requests")
    neighborhood = models.ForeignKey(Neighborhood, on_delete=models.PROTECT, related_name="service_requests")
    assigned_provider = models.ForeignKey(
        "providers.ProviderProfile",
        on_delete=models.PROTECT,
        related_name="assigned_requests",
        blank=True,
        null=True,
    )
    title = models.CharField(max_length=150)
    description = models.CharField(max_length=2000)
    address_detail = models.CharField(max_length=250)
    priority = models.CharField(max_length=6, choices=Priority.choices, default=Priority.NORMAL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CREATED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        permissions = [("dispatch_request", "Peut lancer la recherche de prestataires")]

    def __str__(self):
        return f"{self.title} ({self.pk})"


class RequestStatusHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_request = models.ForeignKey(ServiceRequest, on_delete=models.PROTECT, related_name="status_history")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    previous_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20, choices=ServiceRequest.Status.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["service_request"],
                condition=Q(previous_status="", new_status="CREATED"),
                name="requests_one_initial_history",
            )
        ]

    def __str__(self):
        return f"{self.service_request_id}: {self.previous_status} → {self.new_status}"


class ServiceOffer(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "En attente"
        ACCEPTED = "ACCEPTED", "Acceptée"
        DECLINED = "DECLINED", "Refusée"
        EXPIRED = "EXPIRED", "Expirée"
        CANCELLED = "CANCELLED", "Annulée"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_request = models.ForeignKey(ServiceRequest, on_delete=models.PROTECT, related_name="offers")
    provider = models.ForeignKey("providers.ProviderProfile", on_delete=models.PROTECT, related_name="offers")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.UniqueConstraint(fields=["service_request", "provider"], name="requests_unique_offer_provider"),
            models.UniqueConstraint(
                fields=["service_request"],
                condition=Q(status="ACCEPTED"),
                name="requests_one_accepted_offer",
            ),
        ]

    def __str__(self):
        return f"{self.service_request_id} → {self.provider_id}"
