import uuid

from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

from .managers import UserManager


class User(AbstractUser):
    class Role(models.TextChoices):
        CLIENT = "CLIENT", "Client"
        PROVIDER = "PROVIDER", "Prestataire"
        ADMIN = "ADMIN", "Administrateur"
        SUPERADMIN = "SUPERADMIN", "Super administrateur"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None
    phone = models.CharField(
        max_length=16,
        unique=True,
        validators=[
            RegexValidator(
                regex=r"^\+[1-9]\d{7,14}$",
                message="Utiliser le format international, par exemple +22312345678.",
            )
        ],
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.CLIENT)
    phone_verified_at = models.DateTimeField(blank=True, null=True)

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []
    objects = UserManager()

    def __str__(self):
        return self.phone
