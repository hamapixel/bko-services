from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.providers.models import ProviderProfile

from .models import ProviderSubscription, SubscriptionHistory, SubscriptionPlan


class ProviderPendingPlanCancellationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            phone="+22373110001",
            password="Strong-password-2026!",
            role=User.Role.PROVIDER,
            phone_verified_at=timezone.now(),
        )
        self.provider = ProviderProfile.objects.create(
            user=self.user,
            legal_name="Prestataire changement plan",
            display_name="Prestataire changement plan",
            status=ProviderProfile.Status.VERIFIED,
            is_available=True,
            identity_checked=True,
            verified_at=timezone.now(),
        )
        self.plus = SubscriptionPlan.objects.create(
            code="pending-cancel-plus",
            name="Plus",
            price_xof=4000,
            duration_days=30,
            can_receive_requests=True,
            can_receive_urgent_requests=True,
            max_active_jobs=3,
            is_active=True,
        )
        self.essential = SubscriptionPlan.objects.create(
            code="pending-cancel-essential",
            name="Essentiel",
            price_xof=2000,
            duration_days=30,
            can_receive_requests=True,
            can_receive_urgent_requests=False,
            max_active_jobs=1,
            is_active=True,
        )
        now = timezone.now()
        self.ends_at = now + timedelta(days=30)
        self.subscription = ProviderSubscription.objects.create(
            provider=self.provider,
            plan=self.plus,
            status=ProviderSubscription.Status.ACTIVE,
            starts_at=now - timedelta(days=1),
            ends_at=self.ends_at,
            pending_plan=self.essential,
            pending_starts_at=self.ends_at,
            pending_ends_at=self.ends_at + timedelta(days=30),
        )
        self.api = APIClient()
        self.api.force_login(self.user)

    def test_provider_can_cancel_own_future_plan_change_without_losing_current_plan(self):
        response = self.api.post(
            "/api/v1/subscriptions/me/pending-change/cancel/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.plan, self.plus)
        self.assertEqual(self.subscription.status, ProviderSubscription.Status.ACTIVE)
        self.assertEqual(self.subscription.ends_at, self.ends_at)
        self.assertIsNone(self.subscription.pending_plan)
        self.assertIsNone(self.subscription.pending_starts_at)
        self.assertIsNone(self.subscription.pending_ends_at)

        history = SubscriptionHistory.objects.get(
            subscription=self.subscription,
            action=SubscriptionHistory.Action.PLAN_CANCEL,
        )
        self.assertEqual(history.actor, self.user)
        self.assertEqual(history.plan_code, self.essential.code)
        self.assertIn("annulé", history.note)

    def test_provider_cannot_cancel_when_no_future_change_exists(self):
        self.subscription.pending_plan = None
        self.subscription.pending_starts_at = None
        self.subscription.pending_ends_at = None
        self.subscription.save(
            update_fields=[
                "pending_plan",
                "pending_starts_at",
                "pending_ends_at",
                "updated_at",
            ]
        )

        response = self.api.post(
            "/api/v1/subscriptions/me/pending-change/cancel/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.plan, self.plus)
        self.assertEqual(self.subscription.status, ProviderSubscription.Status.ACTIVE)

    def test_endpoint_rejects_extra_fields(self):
        response = self.api.post(
            "/api/v1/subscriptions/me/pending-change/cancel/",
            {"plan_id": str(self.essential.pk)},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_non_provider_cannot_cancel_provider_change(self):
        User = get_user_model()
        client_user = User.objects.create_user(
            phone="+22373110002",
            password="Strong-password-2026!",
            role=User.Role.CLIENT,
            phone_verified_at=timezone.now(),
        )
        api = APIClient()
        api.force_login(client_user)

        response = api.post(
            "/api/v1/subscriptions/me/pending-change/cancel/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.pending_plan, self.essential)
