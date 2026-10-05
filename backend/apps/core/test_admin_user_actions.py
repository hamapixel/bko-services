from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.providers.models import ProviderProfile


User = get_user_model()


class AdminUserActionsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            phone="+22370001001",
            password="StrongPass123!",
        )
        self.client.force_authenticate(self.admin)

    def test_superadmin_can_deactivate_and_reactivate_user(self):
        user = User.objects.create_user(
            phone="+22370001002",
            password="StrongPass123!",
        )

        response = self.client.patch(
            f"/api/v1/admin/users/{user.pk}/status/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertFalse(user.is_active)

        response = self.client.patch(
            f"/api/v1/admin/users/{user.pk}/status/",
            {"is_active": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_deactivating_provider_keeps_role_and_disables_availability(self):
        user = User.objects.create_user(
            phone="+22370001003",
            password="StrongPass123!",
            role=User.Role.PROVIDER,
        )
        profile = ProviderProfile.objects.create(
            user=user,
            legal_name="Prestataire Test",
            display_name="Prestataire Test",
            status=ProviderProfile.Status.VERIFIED,
            is_available=True,
        )

        response = self.client.patch(
            f"/api/v1/admin/users/{user.pk}/status/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        user.refresh_from_db()
        profile.refresh_from_db()
        self.assertEqual(user.role, User.Role.PROVIDER)
        self.assertFalse(user.is_active)
        self.assertFalse(profile.is_available)

    def test_superadmin_cannot_manage_own_account(self):
        response = self.client.patch(
            f"/api/v1/admin/users/{self.admin.pk}/status/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_delete_unused_user_and_block_account_with_history(self):
        unused = User.objects.create_user(
            phone="+22370001004",
            password="StrongPass123!",
        )
        response = self.client.delete(
            f"/api/v1/admin/users/{unused.pk}/delete/",
        )
        self.assertEqual(response.status_code, 204)
        self.assertFalse(User.objects.filter(pk=unused.pk).exists())

        historical = User.objects.create_user(
            phone="+22370001005",
            password="StrongPass123!",
            role=User.Role.PROVIDER,
        )
        ProviderProfile.objects.create(
            user=historical,
            legal_name="Historique",
            display_name="Historique",
        )

        response = self.client.delete(
            f"/api/v1/admin/users/{historical.pk}/delete/",
        )
        self.assertEqual(response.status_code, 400)
        self.assertTrue(User.objects.filter(pk=historical.pk).exists())

    def test_normal_client_cannot_manage_users(self):
        target = User.objects.create_user(
            phone="+22370001006",
            password="StrongPass123!",
        )
        client_user = User.objects.create_user(
            phone="+22370001007",
            password="StrongPass123!",
        )
        client = APIClient()
        client.force_authenticate(client_user)

        response = client.patch(
            f"/api/v1/admin/users/{target.pk}/status/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
