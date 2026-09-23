import uuid

from django.db import models
from django.db.models.functions import Lower


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "name", "id"]
        verbose_name_plural = "categories"
        constraints = [models.UniqueConstraint(Lower("name"), name="catalog_category_name_ci_unique")]

    def __str__(self):
        return self.name


class Trade(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="trades")
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "name", "id"]
        constraints = [models.UniqueConstraint(Lower("name"), "category", name="catalog_trade_category_name_ci_unique")]

    def __str__(self):
        return f"{self.name} — {self.category.name}"
