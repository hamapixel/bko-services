from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.providers.models import ProviderProfile
from apps.subscriptions.models import ProviderSubscription, SubscriptionPlan

from .models import PaymentTransaction


@override_settings(PAYMENT_PROVIDER="TEST")
class PaymentPlanChangeCheckoutTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            phone="+22374110000",
            password="Strong-admin-2026!",
        )
        self.user = User.objects.create_user(
            phone="+22374110001",
            password="Strong-password-2026!",
            role=User.Role.PROVIDER,
            phone_verified_at=timezone.now(),
        )
        self.provider = ProviderProfile.objects.create(
            user=self.user,
            legal_name="Prestataire checkout plan",
            display_name="Prestataire checkout plan",
            status=ProviderProfile.Status.VERIFIED,
            is_available=True,
            identity_checked=True,
            verified_at=timezone.now(),
            verified_by=self.admin,
        )
        self.essential = SubscriptionPlan.objects.create(
            code="checkout-essential",
            name="Essentiel checkout",
            price_xof=2000,
            duration_days=30,
            can_receive_requests=True,
            can_receive_urgent_requests=False,
            max_active_jobs=1,
            is_active=True,
        )
        self.plus = SubscriptionPlan.objects.create(
            code="checkout-plus",
            name="Plus checkout",
            price_xof=4000,
            duration_days=30,
            can_receive_requests=True,
            can_receive_urgent_requests=True,
            max_active_jobs=3,
            is_active=True,
        )
        self.pro = SubscriptionPlan.objects.create(
            code="checkout-pro",
            name="Pro checkout",
            price_xof=7500,
            duration_days=30,
            can_receive_requests=True,
            can_receive_urgent_requests=True,
            max_active_jobs=None,
            is_active=True,
        )

    def test_checkout_is_blocked_while_future_plan_is_already_scheduled(self):
        now = timezone.now()
        current_end = now + timedelta(days=10)
        ProviderSubscription.objects.create(
            provider=self.provider,
            plan=self.pro,
            pending_plan=self.essential,
            pending_starts_at=current_end,
            pending_ends_at=current_end + timedelta(days=30),
            status=ProviderSubscription.Status.ACTIVE,
            starts_at=now - timedelta(days=5),
            ends_at=current_end,
            activated_by=self.admin,
        )

        api = APIClient()
        api.force_login(self.user)
        response = api.post(
            "/api/v1/payments/transactions/",
            {
                "plan_id": str(self.plus.pk),
                "idempotency_key": "blocked-scheduled-change",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(PaymentTransaction.objects.count(), 0)
        self.assertIn("déjà programmé", str(response.json()))
