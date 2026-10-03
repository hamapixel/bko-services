from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Category, Trade


User = get_user_model()


class AdminPlatformCatalogTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            phone="+22370000001",
            password="StrongPass123!",
        )
        self.client.force_authenticate(self.admin)

    def test_admin_can_create_update_and_deactivate_category(self):
        response = self.client.post(
            "/api/v1/admin/catalog/categories/",
            {
                "name": "Beauté",
                "description": "Services beauté",
                "display_order": 30,
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        category_id = response.json()["id"]

        response = self.client.patch(
            f"/api/v1/admin/catalog/categories/{category_id}/",
            {"name": "Beauté & soins", "is_active": False},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Beauté & soins")
        self.assertFalse(response.json()["is_active"])
        self.assertFalse(Category.objects.get(pk=category_id).is_active)

    def test_admin_can_create_update_and_deactivate_trade(self):
        category = Category.objects.create(name="Bâtiment")
        response = self.client.post(
            "/api/v1/admin/catalog/trades/",
            {
                "category": str(category.pk),
                "name": "Terrassement",
                "description": "Préparation et nivellement de terrain",
                "display_order": 20,
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        trade_id = response.json()["id"]
        self.assertEqual(response.json()["category_name"], "Bâtiment")

        response = self.client.patch(
            f"/api/v1/admin/catalog/trades/{trade_id}/",
            {"name": "Terrassement terrain", "is_active": False},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Terrassement terrain")
        self.assertFalse(Trade.objects.get(pk=trade_id).is_active)

    def test_admin_catalog_rejects_duplicates_and_unknown_fields(self):
        category = Category.objects.create(name="Maison")
        response = self.client.post(
            "/api/v1/admin/catalog/categories/",
            {"name": "MAISON"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

        response = self.client.post(
            "/api/v1/admin/catalog/trades/",
            {
                "category": str(category.pk),
                "name": "Plomberie",
                "unexpected": "nope",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

        Trade.objects.create(category=category, name="Plomberie")
        response = self.client.post(
            "/api/v1/admin/catalog/trades/",
            {"category": str(category.pk), "name": "plomberie"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_non_admin_cannot_manage_catalog(self):
        client = APIClient()
        user = User.objects.create_user(
            phone="+22370000002",
            password="StrongPass123!",
            role=User.Role.CLIENT,
        )
        client.force_authenticate(user)

        self.assertEqual(
            client.get("/api/v1/admin/catalog/categories/").status_code,
            403,
        )
        self.assertEqual(
            client.post(
                "/api/v1/admin/catalog/categories/",
                {"name": "Interdit"},
                format="json",
            ).status_code,
            403,
        )
