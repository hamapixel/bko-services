import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.requests.models import ServiceRequest


class Complaint(models.Model):
    class Category(models.TextChoices):
        SERVICE_QUALITY = "SERVICE_QUALITY", "Qualité du service"
        BEHAVIOR = "BEHAVIOR", "Comportement"
        PAYMENT = "PAYMENT", "Paiement"
        SAFETY = "SAFETY", "Sécurité"
        OTHER = "OTHER", "Autre"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Ouverte"
        UNDER_REVIEW = "UNDER_REVIEW", "En cours d'examen"
        RESOLVED = "RESOLVED", "Résolue"
        REJECTED = "REJECTED", "Rejetée"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.PROTECT,
        related_name="complaints",
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="complaints_reported",
    )
    category = models.CharField(max_length=20, choices=Category.choices)
    description = models.CharField(max_length=2000)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    previous_request_status = models.CharField(
        max_length=20,
        choices=ServiceRequest.Status.choices,
    )
    resolution_note = models.CharField(max_length=2000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["service_request"],
                condition=Q(status__in=["OPEN", "UNDER_REVIEW"]),
                name="complaints_one_active_per_request",
            )
        ]
        indexes = [
            models.Index(
                fields=["status", "-created_at"],
                name="complaints_status_created_idx",
            )
        ]

    def __str__(self):
        return f"{self.service_request_id} — {self.status}"


class ComplaintStatusHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.PROTECT,
        related_name="status_history",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="complaint_status_actions",
    )
    previous_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20, choices=Complaint.Status.choices)
    note = models.CharField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.complaint_id}: {self.previous_status} → {self.new_status}"
