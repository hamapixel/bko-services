import uuid

from django.conf import settings
from django.db import models


class SmsDeliveryLog(models.Model):
    class Purpose(models.TextChoices):
        PHONE_VERIFICATION = "PHONE_VERIFICATION", "Vérification du téléphone"
        PASSWORD_RESET = "PASSWORD_RESET", "Réinitialisation du mot de passe"

    class Provider(models.TextChoices):
        CONSOLE = "CONSOLE", "Console locale"
        TWILIO = "TWILIO", "Twilio"

    class Status(models.TextChoices):
        PENDING = "PENDING", "En attente"
        ACCEPTED = "ACCEPTED", "Accepté par le fournisseur"
        FAILED = "FAILED", "Échec"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="sms_delivery_logs",
        blank=True,
        null=True,
    )
    recipient = models.CharField(max_length=16)
    purpose = models.CharField(max_length=32, choices=Purpose.choices)
    provider = models.CharField(max_length=16, choices=Provider.choices)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    request_ip_hash = models.CharField(max_length=64, blank=True, db_index=True)
    provider_message_id = models.CharField(max_length=64, blank=True)
    provider_status = models.CharField(max_length=32, blank=True)
    error_code = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["recipient", "-created_at"],
                name="sms_recipient_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.purpose} — {self.status}"
