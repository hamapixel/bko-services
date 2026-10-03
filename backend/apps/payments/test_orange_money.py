import os
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.providers.models import ProviderProfile
from apps.subscriptions.models import ProviderSubscription, SubscriptionPlan

from .models import PaymentTransaction


ORANGE_ENV = {
    "ORANGE_MONEY_CLIENT_ID": "orange-client-id",
    "ORANGE_MONEY_CLIENT_SECRET": "orange-client-secret",
    "ORANGE_MONEY_MERCHANT_KEY": "orange-merchant-key",
    "ORANGE_MONEY_COUNTRY": "dev",
    "ORANGE_MONEY_HTTP_TIMEOUT_SECONDS": "8",
}


@override_settings(PAYMENT_RETURN_ORIGIN="https://bko.example", PAYMENT_PROVIDER="GENERIC")
@patch.dict(os.environ, ORANGE_ENV)
class OrangeMoneyPaymentTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            phone="+22375000000",
            password="Strong-admin-2026!",
        )
        user = User.objects.create_user(
            phone="+22375000001",
            password="Strong-password-2026!",
            role="PROVIDER",
            phone_verified_at=timezone.now(),
        )
        self.provider = ProviderProfile.objects.create(
            user=user,
            legal_name="Prestataire Orange",
            display_name="Prestataire Orange",
            status=ProviderProfile.Status.VERIFIED,
            is_available=False,
            identity_checked=True,
            verified_at=timezone.now(),
            verified_by=self.admin,
        )
        self.plan = SubscriptionPlan.objects.create(
            code="orange-plus",
            name="Orange Plus",
            price_xof=4000,
            duration_days=30,
            can_receive_requests=True,
            can_receive_urgent_requests=True,
        )
        self.api = APIClient()
        self.api.force_login(user)
        self.pay_token = "p" * 64
        self.notif_token = "n" * 32

    def orange_reply(self, resource, payload):
        if resource == "webpayment":
            self.assertEqual(payload["merchant_key"], "orange-merchant-key")
            self.assertEqual(payload["currency"], "OUV")
            self.assertEqual(payload["amount"], 4000)
            self.assertEqual(len(payload["order_id"]), 30)
            self.assertEqual(
                payload["notif_url"],
                "https://bko.example/api/v1/payments/webhooks/orange-money/",
            )
            return {
                "status": 201,
                "message": "OK",
                "pay_token": self.pay_token,
                "payment_url": (
                    "https://webpayment-sb.orange-money.com/payment/pay_token/"
                    + self.pay_token
                ),
                "notif_token": self.notif_token,
            }

        self.assertEqual(resource, "transactionstatus")
        self.assertEqual(payload["amount"], 4000)
        self.assertEqual(payload["pay_token"], self.pay_token)
        return {
            "status": "SUCCESS",
            "order_id": payload["order_id"],
            "txnid": "MP-ORANGE-0001",
        }

    @patch("apps.payments.orange_money._orange_request")
    def test_explicit_orange_checkout_and_verified_webhook_activate_once(
        self,
        orange_request,
    ):
        orange_request.side_effect = self.orange_reply

        methods = self.api.get("/api/v1/payments/methods/")
        self.assertEqual(methods.status_code, 200)
        self.assertTrue(methods.json()["orange_money"])
        providers = {
            item["provider"]: item for item in methods.json()["methods"]
        }
        self.assertTrue(providers["ORANGE_MONEY"]["available"])

        created = self.api.post(
            "/api/v1/payments/checkout/",
            {
                "plan_id": str(self.plan.pk),
                "idempotency_key": "orange-checkout-0001",
                "payment_method": "ORANGE_MONEY",
            },
            format="json",
        )
        self.assertEqual(created.status_code, 200)
        self.assertEqual(created.json()["payment_provider"], "ORANGE_MONEY")
        self.assertTrue(
            created.json()["checkout_url"].startswith(
                "https://webpayment-sb.orange-money.com/"
            )
        )

        payment = PaymentTransaction.objects.get()
        self.assertEqual(len(payment.checkout_session_id), 40)
        self.assertNotEqual(payment.checkout_session_id, self.notif_token)
        self.assertFalse(
            ProviderSubscription.objects.filter(provider=self.provider).exists()
        )

        detail = self.api.get(
            f"/api/v1/payments/transactions/{payment.pk}/",
            {"paiement": "retour"},
        )
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["status"], "PENDING")
        self.assertFalse(
            ProviderSubscription.objects.filter(provider=self.provider).exists()
        )

        invalid = APIClient().post(
            "/api/v1/payments/webhooks/orange-money/",
            {"status": "SUCCESS", "notif_token": "wrong-token", "txnid": "forged"},
            format="json",
        )
        self.assertEqual(invalid.status_code, 401)
        self.assertFalse(
            ProviderSubscription.objects.filter(provider=self.provider).exists()
        )

        confirmed = APIClient().post(
            "/api/v1/payments/webhooks/orange-money/",
            {
                "status": "SUCCESS",
                "notif_token": self.notif_token,
                "txnid": "forged-browser-value",
            },
            format="json",
        )
        self.assertEqual(confirmed.status_code, 200)

        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentTransaction.Status.SUCCEEDED)
        self.assertEqual(payment.provider_transaction_id, "MP-ORANGE-0001")
        self.assertIsNotNone(payment.fulfilled_at)
        self.assertEqual(
            ProviderSubscription.objects.filter(provider=self.provider).count(),
            1,
        )

        duplicate = APIClient().post(
            "/api/v1/payments/webhooks/orange-money/",
            {
                "status": "SUCCESS",
                "notif_token": self.notif_token,
                "txnid": "anything",
            },
            format="json",
        )
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(duplicate.json()["result"], "duplicate")
        subscription = ProviderSubscription.objects.get(provider=self.provider)
        self.assertEqual(subscription.history.count(), 1)
        self.assertEqual(orange_request.call_count, 2)

    @patch("apps.payments.orange_money._orange_request")
    def test_pending_status_never_activates_subscription(self, orange_request):
        def reply(resource, payload):
            if resource == "webpayment":
                return self.orange_reply(resource, payload)
            return {
                "status": "PENDING",
                "order_id": payload["order_id"],
                "txnid": "",
            }

        orange_request.side_effect = reply
        created = self.api.post(
            "/api/v1/payments/checkout/",
            {
                "plan_id": str(self.plan.pk),
                "idempotency_key": "orange-pending-0001",
                "payment_method": "ORANGE_MONEY",
            },
            format="json",
        )
        self.assertEqual(created.status_code, 200)

        callback = APIClient().post(
            "/api/v1/payments/webhooks/orange-money/",
            {
                "status": "SUCCESS",
                "notif_token": self.notif_token,
                "txnid": "untrusted-value",
            },
            format="json",
        )
        self.assertEqual(callback.status_code, 200)
        self.assertEqual(callback.json()["result"], "waiting")
        payment = PaymentTransaction.objects.get()
        self.assertEqual(payment.status, PaymentTransaction.Status.PENDING)
        self.assertFalse(
            ProviderSubscription.objects.filter(provider=self.provider).exists()
        )

    def test_orange_is_unavailable_without_merchant_credentials(self):
        with patch.dict(
            os.environ,
            {
                "ORANGE_MONEY_CLIENT_ID": "",
                "ORANGE_MONEY_CLIENT_SECRET": "",
                "ORANGE_MONEY_MERCHANT_KEY": "",
            },
        ):
            methods = self.api.get("/api/v1/payments/methods/")
            self.assertFalse(methods.json()["orange_money"])
            response = self.api.post(
                "/api/v1/payments/checkout/",
                {
                    "plan_id": str(self.plan.pk),
                    "idempotency_key": "orange-disabled-0001",
                    "payment_method": "ORANGE_MONEY",
                },
                format="json",
            )
            self.assertEqual(response.status_code, 503)
            self.assertEqual(PaymentTransaction.objects.count(), 0)

    def test_orange_requires_public_https_return_origin(self):
        with override_settings(PAYMENT_RETURN_ORIGIN="http://localhost:3010"):
            methods = self.api.get("/api/v1/payments/methods/")
            self.assertFalse(methods.json()["orange_money"])
