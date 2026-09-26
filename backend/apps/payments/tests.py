import hashlib
import hmac
import json
from datetime import timedelta
from unittest.mock import patch

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

    def test_expired_subscription_requires_new_confirmed_payment(self):
        now = timezone.now()
        existing = ProviderSubscription.objects.create(
            provider=self.provider,
            plan=self.plan,
            starts_at=now - timedelta(days=31),
            ends_at=now - timedelta(days=1),
            activated_by=self.admin,
        )
        api = APIClient()
        api.force_login(self.provider.user)
        self.assertEqual(
            api.get("/api/v1/subscriptions/me/").json()["subscription"]["status"],
            "EXPIRED",
        )

        created = self.create_payment(key="expired-renew-0001")
        self.assertEqual(created.status_code, 201)
        payment = PaymentTransaction.objects.get()
        self.assertEqual(payment.purpose, PaymentTransaction.Purpose.ACTIVATE)
        # Browser redirects and status reads never extend an expired subscription.
        for result in ("retour", "erreur"):
            detail = api.get(
                "/api/v1/payments/transactions/" + str(payment.pk) + "/",
                {"paiement": result},
            )
            self.assertEqual(detail.json()["status"], "PENDING")
            self.assertEqual(
                api.get("/api/v1/subscriptions/me/").json()["subscription"]["status"],
                "EXPIRED",
            )

        before = timezone.now()
        confirmed, _ = self.signed_webhook(
            payment, provider_transaction_id="provider-txn-expired-renew"
        )
        self.assertEqual(confirmed.status_code, 200)
        existing.refresh_from_db()
        self.assertEqual(existing.status, ProviderSubscription.Status.ACTIVE)
        self.assertGreaterEqual(existing.starts_at, before)
        self.assertEqual(existing.ends_at, existing.starts_at + timedelta(days=30))
        self.assertEqual(
            api.get("/api/v1/subscriptions/me/").json()["subscription"]["status"],
            "ACTIVE",
        )

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


    def test_admin_payment_list_filters_status_safely(self):
        created = self.create_payment()
        self.assertEqual(created.status_code, 201)

        admin = APIClient()
        admin.force_login(self.admin)

        pending = admin.get("/api/v1/payments/admin/transactions/?status=PENDING")
        self.assertEqual(pending.status_code, 200)
        self.assertEqual(pending.json()["count"], 1)

        succeeded = admin.get("/api/v1/payments/admin/transactions/?status=SUCCEEDED")
        self.assertEqual(succeeded.status_code, 200)
        self.assertEqual(succeeded.json()["count"], 0)

        self.assertEqual(
            admin.get("/api/v1/payments/admin/transactions/?status=UNKNOWN").status_code,
            400,
        )

    @override_settings(
        WAVE_API_KEY="wave-test-key",
        WAVE_WEBHOOK_SECRET="wave-test-webhook",
        PAYMENT_RETURN_ORIGIN="https://bko.example",
    )
    @patch("apps.payments.wave._wave_request")
    def test_wave_checkout_requires_signed_matching_payment_before_activation(self, wave_request):
        api = APIClient()
        api.force_login(self.provider.user)

        # Wave echoes the server-created reference, never a browser-supplied amount.
        def wave_reply(method, path, payload=None):
            if method == "GET":
                return {"result": []}
            self.assertEqual(payload["amount"], "5000")
            return_url = (
                "https://bko.example/prestataire/abonnement?transaction="
                + str(PaymentTransaction.objects.get().pk)
            )
            self.assertEqual(payload["success_url"], return_url + "&paiement=retour")
            self.assertEqual(payload["error_url"], return_url + "&paiement=erreur")
            return {
                "id": "cos-test-123",
                "amount": payload["amount"],
                "currency": payload["currency"],
                "client_reference": payload["client_reference"],
                "wave_launch_url": "https://pay.wave.com/c/cos-test-123",
            }

        wave_request.side_effect = wave_reply
        args = {"plan_id": str(self.plan.pk), "idempotency_key": "wave-test-0001"}
        created = api.post("/api/v1/payments/wave/checkout/", args, format="json")
        self.assertEqual(created.status_code, 200)
        self.assertEqual(created.json()["payment_provider"], "WAVE")
        self.assertEqual(created.json()["checkout_url"], "https://pay.wave.com/c/cos-test-123")
        self.assertEqual(
            api.post("/api/v1/payments/wave/checkout/", args, format="json").status_code,
            200,
        )
        self.assertEqual(wave_request.call_count, 2)
        payment = PaymentTransaction.objects.get()
        self.assertFalse(ProviderSubscription.objects.filter(provider=self.provider).exists())
        # The browser can open or forge either return URL: both are read-only.
        for result in ("retour", "erreur"):
            response = api.get(
                "/api/v1/payments/transactions/" + str(payment.pk) + "/",
                {"paiement": result, "transaction": str(payment.pk)},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "PENDING")
            self.assertFalse(ProviderSubscription.objects.filter(provider=self.provider).exists())
        generic, _ = self.signed_webhook(payment)
        self.assertEqual(generic.status_code, 400)
        self.assertFalse(ProviderSubscription.objects.filter(provider=self.provider).exists())

        payload = {
            "id": "EV-test-1", "type": "checkout.session.completed",
            "data": {
                "id": payment.checkout_session_id,
                "client_reference": payment.merchant_reference,
                "transaction_id": "wave-txn-123",
                "payment_status": "succeeded", "checkout_status": "complete",
                "amount": "5000", "currency": "XOF",
            },
        }

        def send(data, *, secret="wave-test-webhook", session_id=None):
            body = json.loads(json.dumps(data))
            if session_id:
                body["data"]["id"] = session_id
            raw = json.dumps(body, separators=(",", ":")).encode("utf-8")
            timestamp = str(int(timezone.now().timestamp()))
            signature = hmac.new(
                secret.encode("utf-8"), timestamp.encode("ascii") + raw, hashlib.sha256
            ).hexdigest()
            return APIClient().generic(
                "POST", "/api/v1/payments/webhooks/wave/", raw,
                content_type="application/json",
                HTTP_WAVE_SIGNATURE=f"t={timestamp},v1={signature}",
            )

        self.assertEqual(send(payload, secret="wrong-secret").status_code, 401)
        self.assertEqual(send(payload, session_id="cos-other-session").status_code, 400)
        mismatch = json.loads(json.dumps(payload))
        mismatch["data"]["amount"] = "100"
        self.assertEqual(send(mismatch).status_code, 400)
        self.assertFalse(ProviderSubscription.objects.filter(provider=self.provider).exists())
        self.assertEqual(send(payload).status_code, 200)
        self.assertEqual(send(payload).status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentTransaction.Status.SUCCEEDED)
        self.assertEqual(ProviderSubscription.objects.filter(provider=self.provider).count(), 1)

    def test_wave_is_unavailable_until_merchant_credentials_are_configured(self):
        api = APIClient()
        api.force_login(self.provider.user)
        self.assertFalse(api.get("/api/v1/payments/methods/").json()["wave"])
        response = api.post(
            "/api/v1/payments/wave/checkout/",
            {"plan_id": str(self.plan.pk), "idempotency_key": "wave-disabled-01"},
            format="json",
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(PaymentTransaction.objects.count(), 0)

    @override_settings(
        WAVE_API_KEY="wave-test-key", WAVE_WEBHOOK_SECRET="wave-test-webhook",
        PAYMENT_RETURN_ORIGIN="http://localhost:3000",
    )
    def test_wave_requires_a_public_https_return_origin(self):
        api = APIClient()
        api.force_login(self.provider.user)
        self.assertFalse(api.get("/api/v1/payments/methods/").json()["wave"])
