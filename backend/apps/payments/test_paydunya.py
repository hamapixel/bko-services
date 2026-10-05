import hashlib
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.providers.models import ProviderProfile
from apps.subscriptions.models import ProviderSubscription, SubscriptionPlan

from .models import PaymentTransaction


PAYDUNYA_SETTINGS = {
    "PAYMENT_PROVIDER": "PAYDUNYA",
    "PAYMENT_RETURN_ORIGIN": "https://bko.test",
    "PAYDUNYA_MASTER_KEY": "master-key-test",
    "PAYDUNYA_PRIVATE_KEY": "private-key-test",
    "PAYDUNYA_TOKEN": "token-test",
    "PAYDUNYA_MODE": "sandbox",
    "PAYDUNYA_CHANNELS": "orange-money-mali",
    "PAYDUNYA_HTTP_TIMEOUT_SECONDS": 2,
}


@override_settings(**PAYDUNYA_SETTINGS)
class PayDunyaPaymentTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            phone="+22373100000",
            password="Strong-admin-2026!",
        )
        self.user = User.objects.create_user(
            phone="+22373100001",
            password="Strong-password-2026!",
            role="PROVIDER",
            phone_verified_at=timezone.now(),
        )
        self.provider = ProviderProfile.objects.create(
            user=self.user,
            legal_name="Prestataire PayDunya",
            display_name="Prestataire PayDunya",
            status=ProviderProfile.Status.VERIFIED,
            is_available=False,
            identity_checked=True,
            verified_at=timezone.now(),
            verified_by=self.admin,
        )
        self.plan = SubscriptionPlan.objects.create(
            code="paydunya-plus",
            name="PayDunya Plus",
            price_xof=4000,
            duration_days=30,
            can_receive_requests=True,
            can_receive_urgent_requests=True,
            max_active_jobs=3,
            is_active=True,
        )
        self.api = APIClient()
        self.api.force_login(self.user)

    @staticmethod
    def _hash():
        return hashlib.sha512(
            PAYDUNYA_SETTINGS["PAYDUNYA_MASTER_KEY"].encode("utf-8")
        ).hexdigest()

    def _start_checkout(self, key="paydunya-key-0001"):
        token = "test_BKO_PAYDUNYA_TOKEN"
        with patch("apps.payments.paydunya._paydunya_request") as mocked:
            mocked.return_value = {
                "response_code": "00",
                "response_text": (
                    "https://app.paydunya.com/sandbox-checkout/invoice/" + token
                ),
                "description": "Checkout Invoice Created",
                "token": token,
            }
            response = self.api.post(
                "/api/v1/payments/checkout/",
                {
                    "plan_id": str(self.plan.pk),
                    "idempotency_key": key,
                    "payment_method": "PAYDUNYA",
                },
                format="json",
            )
        return response, PaymentTransaction.objects.get(idempotency_key=key), token

    def _confirmed(self, payment, token, status="completed", amount=None):
        return {
            "response_code": "00",
            "response_text": "Transaction Found",
            "hash": self._hash(),
            "invoice": {
                "token": token,
                "total_amount": payment.amount_xof if amount is None else amount,
            },
            "custom_data": {
                "merchant_reference": payment.merchant_reference,
                "payment_id": str(payment.pk),
            },
            "mode": "test",
            "status": status,
        }

    def _callback(self, token, callback_hash=None):
        return APIClient().post(
            "/api/v1/payments/webhooks/paydunya/",
            {
                "data": json.dumps(
                    {
                        "hash": callback_hash or self._hash(),
                        "invoice": {"token": token},
                    }
                )
            },
            format="multipart",
        )

    def test_methods_expose_paydunya_when_configured(self):
        response = self.api.get("/api/v1/payments/methods/")
        self.assertEqual(response.status_code, 200)
        methods = {item["provider"]: item for item in response.json()["methods"]}
        self.assertTrue(methods["PAYDUNYA"]["available"])
        self.assertTrue(response.json()["paydunya"])
        self.assertNotIn("cinetpay", response.json())

    def test_checkout_creates_pending_paydunya_transaction(self):
        response, payment, token = self._start_checkout()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payment.payment_provider, "PAYDUNYA")
        self.assertEqual(payment.status, PaymentTransaction.Status.PENDING)
        self.assertEqual(
            payment.checkout_session_id,
            hashlib.sha256(token.encode("utf-8")).hexdigest()[:40],
        )
        self.assertFalse(
            ProviderSubscription.objects.filter(provider=self.provider).exists()
        )

    def test_browser_return_only_redirects_and_never_activates(self):
        _, payment, token = self._start_checkout("paydunya-return-01")
        response = APIClient().get(
            "/api/v1/payments/returns/paydunya/",
            {"token": token},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(str(payment.pk), response["Location"])
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentTransaction.Status.PENDING)
        self.assertFalse(
            ProviderSubscription.objects.filter(provider=self.provider).exists()
        )

    def test_verified_completed_callback_activates_subscription(self):
        _, payment, token = self._start_checkout("paydunya-success-01")
        with patch("apps.payments.paydunya._paydunya_request") as mocked:
            mocked.return_value = self._confirmed(payment, token)
            response = self._callback(token)
        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentTransaction.Status.SUCCEEDED)
        self.assertIsNotNone(payment.fulfilled_at)
        self.assertTrue(
            ProviderSubscription.objects.filter(provider=self.provider).exists()
        )

    def test_invalid_callback_hash_is_rejected_before_status_check(self):
        _, payment, token = self._start_checkout("paydunya-bad-hash-01")
        with patch("apps.payments.paydunya._paydunya_request") as mocked:
            response = self._callback(token, callback_hash="bad-hash")
        self.assertEqual(response.status_code, 401)
        mocked.assert_not_called()
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentTransaction.Status.PENDING)

    def test_amount_mismatch_never_activates_subscription(self):
        _, payment, token = self._start_checkout("paydunya-bad-amount-01")
        with patch("apps.payments.paydunya._paydunya_request") as mocked:
            mocked.return_value = self._confirmed(
                payment, token, amount=payment.amount_xof + 5
            )
            response = self._callback(token)
        self.assertEqual(response.status_code, 400)
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentTransaction.Status.PENDING)
        self.assertFalse(
            ProviderSubscription.objects.filter(provider=self.provider).exists()
        )

    def test_pending_callback_keeps_transaction_pending(self):
        _, payment, token = self._start_checkout("paydunya-pending-01")
        with patch("apps.payments.paydunya._paydunya_request") as mocked:
            mocked.return_value = self._confirmed(payment, token, status="pending")
            response = self._callback(token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"], "waiting")
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentTransaction.Status.PENDING)

    @override_settings(PAYDUNYA_MASTER_KEY="")
    def test_paydunya_unavailable_without_merchant_credentials(self):
        response = self.api.get("/api/v1/payments/methods/")
        self.assertFalse(response.json()["paydunya"])
        checkout = self.api.post(
            "/api/v1/payments/checkout/",
            {
                "plan_id": str(self.plan.pk),
                "idempotency_key": "paydunya-disabled-01",
                "payment_method": "PAYDUNYA",
            },
            format="json",
        )
        self.assertEqual(checkout.status_code, 503)
        self.assertEqual(PaymentTransaction.objects.count(), 0)
