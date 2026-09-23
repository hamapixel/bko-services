import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class Notification(models.Model):
    class Kind(models.TextChoices):
        OFFER_RECEIVED = "OFFER_RECEIVED", "Nouvelle offre"
        REQUEST_ACCEPTED = "REQUEST_ACCEPTED", "Demande attribuée"
        OFFER_CANCELLED = "OFFER_CANCELLED", "Offre annulée"
        PROVIDER_EN_ROUTE = "PROVIDER_EN_ROUTE", "Prestataire en route"
        PROVIDER_ARRIVED = "PROVIDER_ARRIVED", "Prestataire arrivé"
        WORK_STARTED = "WORK_STARTED", "Intervention commencée"
        PROVIDER_COMPLETED = "PROVIDER_COMPLETED", "Intervention terminée"
        CLIENT_CONFIRMED = "CLIENT_CONFIRMED", "Fin confirmée"
        REVIEW_RECEIVED = "REVIEW_RECEIVED", "Avis reçu"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="notifications",
    )
    kind = models.CharField(max_length=32, choices=Kind.choices)
    title = models.CharField(max_length=160)
    message = models.CharField(max_length=500)
    service_request = models.ForeignKey(
        "requests.ServiceRequest",
        on_delete=models.PROTECT,
        related_name="notifications",
        blank=True,
        null=True,
    )
    read_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["recipient", "read_at", "-created_at"],
                name="notif_rec_read_created_idx",
            )
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["recipient", "service_request", "kind"],
                condition=Q(service_request__isnull=False),
                name="notifications_unique_request_event",
            )
        ]

    def __str__(self):
        return f"{self.recipient_id} — {self.kind}"
