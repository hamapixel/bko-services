from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Category, Trade


class CatalogTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name="Maison", description="Services à domicile")
        self.trade = Trade.objects.create(category=self.category, name="Plomberie", description="Réparations")

    def test_public_lists_are_read_only_filtered_and_hide_inactive_parents(self):
        initial_categories = self.client.get("/api/v1/catalog/categories/").json()["count"]
        initial_trades = self.client.get("/api/v1/catalog/trades/").json()["count"]
        other = Category.objects.create(name="Autre catégorie")
        other_trade = Trade.objects.create(category=other, name="Plomberie")

        categories = self.client.get("/api/v1/catalog/categories/")
        self.assertEqual(categories.status_code, 200)
        self.assertEqual(categories.json()["count"], initial_categories + 1)
        trades = self.client.get(f"/api/v1/catalog/trades/?category={self.category.pk}")
        self.assertEqual([row["id"] for row in trades.json()["results"]], [str(self.trade.pk)])
        self.assertNotIn(str(other_trade.pk), str(trades.json()))
        self.assertEqual(self.client.get("/api/v1/catalog/trades/?category=bad").status_code, 400)
        self.assertEqual(self.client.post("/api/v1/catalog/categories/", {"name": "Faux"}).status_code, 405)

        self.trade.is_active = False
        self.trade.save(update_fields=["is_active"])
        self.assertEqual(self.client.get("/api/v1/catalog/trades/").json()["count"], initial_trades)
        self.trade.is_active = True
        self.trade.save(update_fields=["is_active"])
        self.category.is_active = False
        self.category.save(update_fields=["is_active"])
        self.assertEqual(self.client.get("/api/v1/catalog/categories/").json()["count"], initial_categories)
        self.assertEqual(self.client.get(f"/api/v1/catalog/trades/?category={self.category.pk}").json()["count"], 0)

    def test_names_are_unique_without_case_differences_within_parent(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Category.objects.create(name="MAISON")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Trade.objects.create(category=self.category, name="plomberie")
        other = Category.objects.create(name="Artisanat")
        self.assertIsNotNone(Trade.objects.create(category=other, name="Plomberie").pk)
