from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.providers.models import ProviderProfile

from .models import ProviderSubscription, SubscriptionHistory, SubscriptionPlan


class ProviderSelfTrialTests(TestCase):
    def setUp(self):
        self.plan = SubscriptionPlan.objects.update_or_create(
            code="essai-14j",
            defaults={
                "name": "Essai 14 jours",
                "description": "Essai prestataire",
                "price_xof": 0,
                "duration_days": 14,
                "can_receive_requests": True,
                "can_receive_urgent_requests": True,
                "max_active_jobs": 1,
                "is_active": True,
                "display_order": 0,
            },
        )[0]
        self.provider = self._create_provider("+22374000101")

    def _create_provider(self, phone):
        user = get_user_model().objects.create_user(
            phone=phone,
            password="Strong-password-2026!",
            role="PROVIDER",
            phone_verified_at=timezone.now(),
        )
        return ProviderProfile.objects.create(
            user=user,
            legal_name="Prestataire test",
            display_name="Prestataire test",
            status=ProviderProfile.Status.VERIFIED,
            identity_checked=True,
            verified_at=timezone.now(),
            is_available=False,
        )

    def test_verified_provider_can_activate_trial_once(self):
        api = APIClient()
        api.force_login(self.provider.user)
        before = timezone.now()

        response = api.post("/api/v1/subscriptions/trial/activate/", {}, format="json")

        self.assertEqual(response.status_code, 201)
        subscription = ProviderSubscription.objects.get(provider=self.provider)
        self.assertEqual(subscription.plan, self.plan)
        self.assertEqual(subscription.status, ProviderSubscription.Status.ACTIVE)
        self.assertIsNotNone(subscription.free_trial_used_at)
        self.assertGreaterEqual(subscription.starts_at, before)
        self.assertEqual(
            subscription.ends_at,
            subscription.starts_at + timedelta(days=14),
        )
        history = SubscriptionHistory.objects.get(subscription=subscription)
        self.assertEqual(history.action, SubscriptionHistory.Action.ACTIVATED)
        self.assertEqual(history.actor, self.provider.user)

        second = api.post("/api/v1/subscriptions/trial/activate/", {}, format="json")
        self.assertEqual(second.status_code, 400)
        self.assertEqual(ProviderSubscription.objects.filter(provider=self.provider).count(), 1)

    def test_client_cannot_activate_provider_trial(self):
        client_user = get_user_model().objects.create_user(
            phone="+22374000102",
            password="Strong-password-2026!",
            role="CLIENT",
            phone_verified_at=timezone.now(),
        )
        api = APIClient()
        api.force_login(client_user)

        response = api.post("/api/v1/subscriptions/trial/activate/", {}, format="json")

        self.assertEqual(response.status_code, 403)
        self.assertFalse(ProviderSubscription.objects.filter(provider=self.provider).exists())

    def test_trial_is_blocked_after_any_paid_subscription_history(self):
        paid = SubscriptionPlan.objects.create(
            code="paid-before-trial",
            name="Payant avant essai",
            price_xof=2000,
            duration_days=30,
            can_receive_requests=True,
            is_active=True,
        )
        ProviderSubscription.objects.create(
            provider=self.provider,
            plan=paid,
            status=ProviderSubscription.Status.EXPIRED,
            starts_at=timezone.now() - timedelta(days=31),
            ends_at=timezone.now() - timedelta(days=1),
        )
        api = APIClient()
        api.force_login(self.provider.user)

        response = api.post("/api/v1/subscriptions/trial/activate/", {}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            ProviderSubscription.objects.get(provider=self.provider).plan,
            paid,
        )

    def test_inactive_trial_plan_cannot_be_claimed(self):
        self.plan.is_active = False
        self.plan.save(update_fields=["is_active", "updated_at"])
        api = APIClient()
        api.force_login(self.provider.user)

        response = api.post("/api/v1/subscriptions/trial/activate/", {}, format="json")

        self.assertEqual(response.status_code, 404)
        self.assertFalse(ProviderSubscription.objects.filter(provider=self.provider).exists())
