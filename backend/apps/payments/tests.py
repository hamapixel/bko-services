import hashlib
import hmac
import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.providers.models import ProviderProfile
from apps.subscriptions.models import ProviderSubscription, SubscriptionPlan

from .models import PaymentTransaction, PaymentWebhookEvent


class PaymentTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            phone="+22374000000",
            password="Strong-admin-2026!",
        )
        self.client_user = User.objects.create_user(
            phone="+22374000001",
            password="Strong-password-2026!",
            phone_verified_at=timezone.now(),
        )
        self.provider = self.create_provider(
            "+22374000010",
            "Prestataire paiement",
        )
        self.other_provider = self.create_provider(
            "+22374000011",
            "Autre prestataire",
        )
        self.plan = SubscriptionPlan.objects.create(
            code="pay-standard",
            name="Pay Standard",
            price_xof=5000,
            duration_days=30,
            can_receive_requests=True,
            can_receive_urgent_requests=False,
        )
        self.other_plan = SubscriptionPlan.objects.create(
            code="pay-plus",
            name="Pay Plus",
            price_xof=10000,
            duration_days=60,
            can_receive_requests=True,
            can_receive_urgent_requests=True,
        )

    def create_provider(self, phone, name):
        user = get_user_model().objects.create_user(
            phone=phone,
            password="Strong-password-2026!",
            role="PROVIDER",
            phone_verified_at=timezone.now(),
        )
        return ProviderProfile.objects.create(
            user=user,
            legal_name=name,
            display_name=name,
            status=ProviderProfile.Status.VERIFIED,
            is_available=False,
            identity_checked=True,
            verified_at=timezone.now(),
            verified_by=self.admin,
        )

    def create_payment(self, provider=None, plan=None, key="pay-test-key-0001"):
        provider = provider or self.provider
        plan = plan or self.plan
        api = APIClient()
        api.force_login(provider.user)
        return api.post(
            "/api/v1/payments/transactions/",
            {
                "plan_id": str(plan.pk),
                "idempotency_key": key,
            },
            format="json",
        )

    def signed_webhook(
        self,
        payment,
        *,
        reported_status="SUCCESS",
        provider_transaction_id="provider-txn-0001",
        amount_xof=None,
        currency="XOF",
        secret="test-payment-webhook-secret",
        mutate=None,
    ):
        payload = {
            "merchant_reference": payment.merchant_reference,
            "provider_transaction_id": provider_transaction_id,
            "status": reported_status,
            "amount_xof": payment.amount_xof if amount_xof is None else amount_xof,
            "currency": currency,
        }
        if mutate:
            mutate(payload)
        raw = json.dumps(
            payload,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        signature = hmac.new(
            secret.encode("utf-8"),
            raw,
            hashlib.sha256,
        ).hexdigest()
        response = APIClient().generic(
            "POST",
            "/api/v1/payments/webhooks/provider/",
            data=raw,
            content_type="application/json",
            HTTP_X_BKO_PAYMENT_SIGNATURE=signature,
        )
        return response, raw

    def test_provider_creates_pending_payment_with_frozen_terms(self):
        response = self.create_payment()

        self.assertEqual(response.status_code, 201)
        payment = PaymentTransaction.objects.get()
        self.assertEqual(payment.provider, self.provider)
        self.assertEqual(payment.plan, self.plan)
        self.assertEqual(payment.amount_xof, 5000)
        self.assertEqual(payment.currency, "XOF")
        self.assertEqual(payment.duration_days_snapshot, 30)
        self.assertEqual(payment.plan_code_snapshot, "pay-standard")
        self.assertEqual(payment.status, PaymentTransaction.Status.PENDING)
        self.assertEqual(payment.purpose, PaymentTransaction.Purpose.ACTIVATE)
        self.assertTrue(payment.merchant_reference.startswith("BKO-"))
        self.assertFalse(
            ProviderSubscription.objects.filter(provider=self.provider).exists()
        )

    def test_creation_is_idempotent_and_key_cannot_change_plan(self):
        first = self.create_payment(key="same-key-0001")
        second = self.create_payment(key="same-key-0001")

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["id"], second.json()["id"])
        self.assertEqual(PaymentTransaction.objects.count(), 1)

        changed = self.create_payment(
            plan=self.other_plan,
            key="same-key-0001",
        )
        self.assertEqual(changed.status_code, 400)
        self.assertEqual(PaymentTransaction.objects.count(), 1)

    def test_only_verified_provider_can_create_payment(self):
        client = APIClient()
        client.force_login(self.client_user)
        denied = client.post(
            "/api/v1/payments/transactions/",
            {
                "plan_id": str(self.plan.pk),
                "idempotency_key": "client-key-0001",
            },
            format="json",
        )
        self.assertEqual(denied.status_code, 403)

        self.provider.status = ProviderProfile.Status.SUSPENDED
        self.provider.save(update_fields=["status"])
        denied_provider = self.create_payment(key="suspended-key-0001")
        self.assertEqual(denied_provider.status_code, 403)

    def test_payment_list_and_detail_are_private(self):
        created = self.create_payment()
        payment_id = created.json()["id"]

        own = APIClient()
        own.force_login(self.provider.user)
        self.assertEqual(
            own.get("/api/v1/payments/transactions/").json()["count"],
            1,
        )
        self.assertEqual(
            own.get(f"/api/v1/payments/transactions/{payment_id}/").status_code,
            200,
        )

        foreign = APIClient()
        foreign.force_login(self.other_provider.user)
        self.assertEqual(
            foreign.get("/api/v1/payments/transactions/").json()["count"],
            0,
        )
        self.assertEqual(
            foreign.get(
                f"/api/v1/payments/transactions/{payment_id}/"
            ).status_code,
            404,
        )

    def test_invalid_webhook_signature_is_rejected(self):
        self.create_payment()
        payment = PaymentTransaction.objects.get()
        payload = {
            "merchant_reference": payment.merchant_reference,
            "provider_transaction_id": "provider-txn-invalid-signature",
            "status": "SUCCESS",
            "amount_xof": payment.amount_xof,
            "currency": "XOF",
        }
        raw = json.dumps(payload).encode("utf-8")

        response = APIClient().generic(
            "POST",
            "/api/v1/payments/webhooks/provider/",
            data=raw,
            content_type="application/json",
            HTTP_X_BKO_PAYMENT_SIGNATURE="bad-signature",
        )

        self.assertEqual(response.status_code, 401)
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentTransaction.Status.PENDING)
        self.assertEqual(PaymentWebhookEvent.objects.count(), 0)

    @override_settings(PAYMENT_WEBHOOK_SECRET="")
    def test_webhook_is_unavailable_without_secret(self):
        self.create_payment()
        payment = PaymentTransaction.objects.get()
        payload = {
            "merchant_reference": payment.merchant_reference,
            "provider_transaction_id": "provider-txn-no-secret",
            "status": "SUCCESS",
            "amount_xof": payment.amount_xof,
            "currency": "XOF",
        }
        raw = json.dumps(payload).encode("utf-8")

        response = APIClient().generic(
            "POST",
            "/api/v1/payments/webhooks/provider/",
            data=raw,
            content_type="application/json",
            HTTP_X_BKO_PAYMENT_SIGNATURE="anything",
        )

        self.assertEqual(response.status_code, 503)

    def test_success_webhook_activates_subscription_exactly_once(self):
        self.create_payment()
        payment = PaymentTransaction.objects.get()

        first, _ = self.signed_webhook(payment)
        self.assertEqual(first.status_code, 200)

        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentTransaction.Status.SUCCEEDED)
        self.assertIsNotNone(payment.confirmed_at)
        self.assertIsNotNone(payment.fulfilled_at)
        self.assertIsNotNone(payment.subscription_id)

        subscription = ProviderSubscription.objects.get(provider=self.provider)
        first_end = subscription.ends_at
        self.assertEqual(subscription.plan, self.plan)
        self.assertEqual(subscription.history.count(), 1)

        duplicate, _ = self.signed_webhook(payment)
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(duplicate.json()["result"], "duplicate")

        subscription.refresh_from_db()
        self.assertEqual(subscription.ends_at, first_end)
        self.assertEqual(subscription.history.count(), 1)
        self.assertEqual(PaymentWebhookEvent.objects.count(), 1)

    def test_amount_mismatch_is_audited_without_confirming_payment(self):
        self.create_payment()
        payment = PaymentTransaction.objects.get()

        response, _ = self.signed_webhook(
            payment,
            amount_xof=payment.amount_xof + 1,
            provider_transaction_id="provider-txn-bad-amount",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["result"], "rejected_amount")
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentTransaction.Status.PENDING)
        self.assertIsNone(payment.fulfilled_at)
        event = PaymentWebhookEvent.objects.get()
        self.assertFalse(event.accepted)
        self.assertEqual(event.error_code, "amount_or_currency_mismatch")
        self.assertFalse(
            ProviderSubscription.objects.filter(provider=self.provider).exists()
        )

    def test_failed_webhook_is_terminal_and_does_not_activate_subscription(self):
        self.create_payment()
        payment = PaymentTransaction.objects.get()

        response, _ = self.signed_webhook(
            payment,
            reported_status="FAILED",
            provider_transaction_id="provider-txn-failed",
        )

        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentTransaction.Status.FAILED)
        self.assertIsNone(payment.confirmed_at)
        self.assertIsNone(payment.fulfilled_at)
        self.assertFalse(
            ProviderSubscription.objects.filter(provider=self.provider).exists()
        )

        conflict, _ = self.signed_webhook(
            payment,
            reported_status="SUCCESS",
            provider_transaction_id="provider-txn-failed",
            mutate=lambda payload: payload.update({"retry_marker": "x"}),
        )
        self.assertEqual(conflict.status_code, 400)

    def test_successful_payment_renews_existing_subscription(self):
        now = timezone.now()
        existing = ProviderSubscription.objects.create(
            provider=self.provider,
            plan=self.plan,
            starts_at=now - timedelta(days=5),
            ends_at=now + timedelta(days=10),
            activated_by=self.admin,
        )
        old_end = existing.ends_at

        created = self.create_payment(key="renew-key-0001")
        self.assertEqual(created.status_code, 201)
        payment = PaymentTransaction.objects.get()
        self.assertEqual(payment.purpose, PaymentTransaction.Purpose.RENEW)

        response, _ = self.signed_webhook(
            payment,
            provider_transaction_id="provider-txn-renew",
        )
        self.assertEqual(response.status_code, 200)

        existing.refresh_from_db()
        self.assertEqual(existing.ends_at, old_end + timedelta(days=30))
        self.assertEqual(existing.history.count(), 1)

    def test_payment_uses_price_and_duration_snapshots_after_plan_change(self):
        self.create_payment(key="snapshot-key-0001")
        payment = PaymentTransaction.objects.get()
        self.plan.price_xof = 99999
        self.plan.duration_days = 90
        self.plan.name = "Plan changé"
        self.plan.save(
            update_fields=["price_xof", "duration_days", "name", "updated_at"]
        )

        before = timezone.now()
        response, _ = self.signed_webhook(
            payment,
            provider_transaction_id="provider-txn-snapshot",
        )
        self.assertEqual(response.status_code, 200)

        subscription = ProviderSubscription.objects.get(provider=self.provider)
        self.assertGreaterEqual(
            subscription.ends_at,
            before + timedelta(days=30) - timedelta(seconds=2),
        )
        self.assertLess(
            subscription.ends_at,
            before + timedelta(days=31),
        )
        payment.refresh_from_db()
        self.assertEqual(payment.amount_xof, 5000)
        self.assertEqual(payment.duration_days_snapshot, 30)
        self.assertEqual(payment.plan_name_snapshot, "Pay Standard")

    def test_provider_transaction_id_cannot_be_reused(self):
        self.create_payment(key="provider-ref-key-0001")
        first = PaymentTransaction.objects.get()
        response, _ = self.signed_webhook(
            first,
            reported_status="FAILED",
            provider_transaction_id="shared-provider-reference",
        )
        self.assertEqual(response.status_code, 200)

        self.create_payment(key="provider-ref-key-0002")
        second = PaymentTransaction.objects.exclude(pk=first.pk).get()
        reused, _ = self.signed_webhook(
            second,
            provider_transaction_id="shared-provider-reference",
        )

        self.assertEqual(reused.status_code, 400)
        self.assertEqual(
            reused.json()["result"],
            "rejected_provider_reference",
        )
        second.refresh_from_db()
        self.assertEqual(second.status, PaymentTransaction.Status.PENDING)
        self.assertEqual(
            PaymentWebhookEvent.objects.filter(
                transaction=second,
                error_code="provider_transaction_reused",
            ).count(),
            1,
        )

    def test_paid_but_unfulfilled_transaction_can_be_retried_by_admin(self):
        self.create_payment(key="fulfillment-key-0001")
        payment = PaymentTransaction.objects.get()

        self.provider.status = ProviderProfile.Status.SUSPENDED
        self.provider.save(update_fields=["status"])

        response, _ = self.signed_webhook(
            payment,
            provider_transaction_id="provider-txn-fulfillment",
        )
        self.assertEqual(response.status_code, 200)

        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentTransaction.Status.SUCCEEDED)
        self.assertIsNone(payment.fulfilled_at)
        self.assertEqual(
            payment.fulfillment_error_code,
            "subscription_fulfillment_failed",
        )

        self.provider.status = ProviderProfile.Status.VERIFIED
        self.provider.save(update_fields=["status"])

        admin = APIClient()
        admin.force_login(self.admin)
        retried = admin.post(
            f"/api/v1/payments/admin/transactions/{payment.pk}/retry-fulfillment/",
            {},
            format="json",
        )
        self.assertEqual(retried.status_code, 200)

        payment.refresh_from_db()
        self.assertIsNotNone(payment.fulfilled_at)
        self.assertEqual(payment.fulfillment_error_code, "")
        self.assertTrue(
            ProviderSubscription.objects.filter(provider=self.provider).exists()
        )

    def test_non_admin_cannot_access_payment_audit(self):
        self.create_payment()
        api = APIClient()
        api.force_login(self.provider.user)

        self.assertEqual(
            api.get("/api/v1/payments/admin/transactions/").status_code,
            403,
        )
