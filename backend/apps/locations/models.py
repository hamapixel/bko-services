import uuid

from django.db import models
from django.db.models.functions import Lower


class City(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "id"]
        verbose_name_plural = "cities"
        constraints = [models.UniqueConstraint(Lower("name"), name="locations_city_name_ci_unique")]

    def __str__(self):
        return self.name


class Commune(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    city = models.ForeignKey(City, related_name="communes", on_delete=models.PROTECT)
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [models.UniqueConstraint(Lower("name"), "city", name="locations_commune_city_name_ci_unique")]

    def __str__(self):
        return f"{self.name} — {self.city.name}"


class Neighborhood(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    commune = models.ForeignKey(Commune, related_name="neighborhoods", on_delete=models.PROTECT)
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(Lower("name"), "commune", name="locations_neighborhood_commune_name_ci_unique")
        ]

    def __str__(self):
        return f"{self.name} — {self.commune}"
