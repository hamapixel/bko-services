import hashlib
import hmac
from urllib.parse import urlencode
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.providers.models import ProviderProfile
from apps.subscriptions.models import ProviderSubscription, SubscriptionPlan

from .models import PaymentTransaction


CINETPAY_SETTINGS = {
    "PAYMENT_PROVIDER": "CINETPAY",
    "PAYMENT_RETURN_ORIGIN": "https://bko.test",
    "CINETPAY_API_KEY": "test-api-key",
    "CINETPAY_SITE_ID": "123456",
    "CINETPAY_SECRET_KEY": "test-secret-key",
    "CINETPAY_CHANNELS": "MOBILE_MONEY",
    "CINETPAY_HTTP_TIMEOUT_SECONDS": 2,
}

HMAC_FIELDS = (
    "cpm_site_id",
    "cpm_trans_id",
    "cpm_trans_date",
    "cpm_amount",
    "cpm_currency",
    "signature",
    "payment_method",
    "cel_phone_num",
    "cpm_phone_prefixe",
    "cpm_language",
    "cpm_version",
    "cpm_payment_config",
    "cpm_page_action",
    "cpm_custom",
    "cpm_designation",
    "cpm_error_message",
)


@override_settings(**CINETPAY_SETTINGS)
class CinetPayPaymentTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            phone="+22373000000",
            password="Strong-admin-2026!",
        )
        self.user = User.objects.create_user(
            phone="+22373000001",
            password="Strong-password-2026!",
            role="PROVIDER",
            phone_verified_at=timezone.now(),
        )
        self.provider = ProviderProfile.objects.create(
            user=self.user,
            legal_name="Prestataire CinetPay",
            display_name="Prestataire CinetPay",
            status=ProviderProfile.Status.VERIFIED,
            is_available=False,
            identity_checked=True,
            verified_at=timezone.now(),
            verified_by=self.admin,
        )
        self.plan = SubscriptionPlan.objects.create(
            code="cinetpay-plus",
            name="CinetPay Plus",
            price_xof=4000,
            duration_days=30,
            can_receive_requests=True,
            can_receive_urgent_requests=True,
            max_active_jobs=3,
            is_active=True,
        )
        self.api = APIClient()
        self.api.force_login(self.user)

    def _start_checkout(self, key="cinetpay-key-0001"):
        with patch("apps.payments.cinetpay._cinetpay_request") as mocked:
            mocked.return_value = {
                "code": "201",
                "message": "CREATED",
                "data": {
                    "payment_token": "test-token",
                    "payment_url": "https://checkout.cinetpay.com/payment/test-token",
                },
            }
            response = self.api.post(
                "/api/v1/payments/checkout/",
                {"plan_id": str(self.plan.pk), "idempotency_key": key},
                format="json",
            )
        return response, PaymentTransaction.objects.get(idempotency_key=key)

    def _notification(self, payment, *, token=None):
        payload = {
            "cpm_site_id": "123456",
            "cpm_trans_id": payment.checkout_session_id,
            "cpm_trans_date": "2026-10-02 18:00:00",
            "cpm_amount": str(payment.amount_xof),
            "cpm_currency": "XOF",
            "signature": "cinetpay-signature",
            "payment_method": "OMML",
            "cel_phone_num": "73000001",
            "cpm_phone_prefixe": "223",
            "cpm_language": "fr",
            "cpm_version": "V4",
            "cpm_payment_config": "Single",
            "cpm_page_action": "Payment",
            "cpm_custom": payment.merchant_reference,
            "cpm_designation": "Abonnement BKO Services",
            "cpm_error_message": "",
        }
        if token is None:
            message = "".join(str(payload.get(field, "") or "") for field in HMAC_FIELDS)
            token = hmac.new(
                CINETPAY_SETTINGS["CINETPAY_SECRET_KEY"].encode("utf-8"),
                message.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
        return APIClient().generic(
            "POST",
            "/api/v1/payments/webhooks/cinetpay/",
            data=urlencode(payload),
            content_type="application/x-www-form-urlencoded",
            HTTP_X_TOKEN=token,
        )

    def test_methods_expose_cinetpay_when_configured(self):
        response = self.api.get("/api/v1/payments/methods/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["checkout"]["provider"], "CINETPAY")
        self.assertEqual(response.json()["checkout"]["label"], "CinetPay")
        self.assertTrue(response.json()["checkout"]["available"])
        # Orange Money direct is exposed independently from CinetPay.
        self.assertFalse(response.json()["orange_money"])

    def test_checkout_creates_pending_cinetpay_transaction(self):
        response, payment = self._start_checkout()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payment.payment_provider, "CINETPAY")
        self.assertEqual(payment.status, PaymentTransaction.Status.PENDING)
        self.assertEqual(payment.checkout_session_id, payment.pk.hex.upper())
        self.assertEqual(
            payment.checkout_url,
            "https://checkout.cinetpay.com/payment/test-token",
        )
        self.assertFalse(
            ProviderSubscription.objects.filter(provider=self.provider).exists()
        )

    def test_verified_accepted_webhook_activates_subscription(self):
        _, payment = self._start_checkout()
        with patch("apps.payments.cinetpay._cinetpay_request") as mocked:
            mocked.return_value = {
                "code": "00",
                "message": "SUCCES",
                "data": {
                    "amount": str(payment.amount_xof),
                    "currency": "XOF",
                    "status": "ACCEPTED",
                    "payment_method": "OMML",
                    "operator_id": "OMML-TEST-0001",
                    "metadata": payment.merchant_reference,
                },
            }
            response = self._notification(payment)

        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentTransaction.Status.SUCCEEDED)
        self.assertIsNotNone(payment.confirmed_at)
        self.assertIsNotNone(payment.fulfilled_at)
        subscription = ProviderSubscription.objects.get(provider=self.provider)
        self.assertEqual(subscription.plan, self.plan)
        self.assertEqual(subscription.status, ProviderSubscription.Status.ACTIVE)

    def test_waiting_webhook_never_activates_subscription(self):
        _, payment = self._start_checkout()
        with patch("apps.payments.cinetpay._cinetpay_request") as mocked:
            mocked.return_value = {
                "code": "662",
                "message": "WAITING_CUSTOMER_PAYMENT",
                "data": {
                    "amount": str(payment.amount_xof),
                    "currency": "XOF",
                    "status": "WAITING_FOR_CUSTOMER",
                    "operator_id": None,
                },
            }
            response = self._notification(payment)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"], "waiting")
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentTransaction.Status.PENDING)
        self.assertFalse(
            ProviderSubscription.objects.filter(provider=self.provider).exists()
        )

    def test_invalid_hmac_is_rejected_before_status_check(self):
        _, payment = self._start_checkout()
        with patch("apps.payments.cinetpay._cinetpay_request") as mocked:
            response = self._notification(payment, token="bad-token")
        self.assertEqual(response.status_code, 401)
        mocked.assert_not_called()
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentTransaction.Status.PENDING)

    def test_verified_amount_mismatch_does_not_activate_subscription(self):
        _, payment = self._start_checkout()
        with patch("apps.payments.cinetpay._cinetpay_request") as mocked:
            mocked.return_value = {
                "code": "00",
                "message": "SUCCES",
                "data": {
                    "amount": str(payment.amount_xof + 5),
                    "currency": "XOF",
                    "status": "ACCEPTED",
                    "payment_method": "OMML",
                    "operator_id": "OMML-TEST-BAD-AMOUNT",
                },
            }
            response = self._notification(payment)

        self.assertEqual(response.status_code, 400)
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentTransaction.Status.PENDING)
        self.assertIsNone(payment.fulfilled_at)
        self.assertFalse(
            ProviderSubscription.objects.filter(provider=self.provider).exists()
        )
