from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.providers.models import ProviderProfile
from apps.subscriptions.models import SubscriptionPlan

from .models import PaymentTransaction


class RetiredOrangeMoneyDirectTests(TestCase):
    def setUp(self):
        User = get_user_model()
        user = User.objects.create_user(
            phone="+22375000001",
            password="Strong-password-2026!",
            role=User.Role.PROVIDER,
            phone_verified_at=timezone.now(),
        )
        self.provider = ProviderProfile.objects.create(
            user=user,
            legal_name="Prestataire paiement",
            display_name="Prestataire paiement",
            status=ProviderProfile.Status.VERIFIED,
            is_available=False,
            identity_checked=True,
            verified_at=timezone.now(),
        )
        self.plan = SubscriptionPlan.objects.create(
            code="payment-plus",
            name="Plus",
            price_xof=4000,
            duration_days=30,
            can_receive_requests=True,
            can_receive_urgent_requests=True,
        )
        self.api = APIClient()
        self.api.force_login(user)

    def test_public_payment_methods_only_offer_paydunya_and_wave(self):
        response = self.api.get("/api/v1/payments/methods/")
        self.assertEqual(response.status_code, 200)
        providers = [item["provider"] for item in response.json()["methods"]]
        self.assertEqual(providers, ["PAYDUNYA", "WAVE"])
        self.assertNotIn("orange_money", response.json())

    def test_orange_money_direct_cannot_be_selected(self):
        response = self.api.post(
            "/api/v1/payments/checkout/",
            {
                "plan_id": str(self.plan.pk),
                "idempotency_key": "orange-retired-0001",
                "payment_method": "ORANGE_MONEY",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(PaymentTransaction.objects.count(), 0)

    def test_old_orange_webhook_route_is_not_exposed(self):
        response = APIClient().post(
            "/api/v1/payments/webhooks/orange-money/",
            {"status": "SUCCESS"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
