import hashlib
import hmac

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.providers.models import ProviderProfile
from apps.subscriptions.models import ProviderSubscription, SubscriptionPlan
from apps.subscriptions.services import apply_paid_subscription

from .models import PaymentTransaction, PaymentWebhookEvent


class PaymentConfigurationError(Exception):
    pass


class InvalidPaymentSignature(Exception):
    pass


TERMINAL_STATUSES = {
    PaymentTransaction.Status.SUCCEEDED,
    PaymentTransaction.Status.FAILED,
    PaymentTransaction.Status.CANCELLED,
}


def can_manage_payments(user):
    return bool(
        user
        and user.is_authenticated
        and user.is_active
        and user.is_staff
        and (
            user.is_superuser
            or (
                user.role == user.Role.ADMIN
                and user.has_perm("payments.manage_payments")
            )
        )
    )


def verify_webhook_signature(raw_body, signature):
    secret = settings.PAYMENT_WEBHOOK_SECRET
    if not secret:
        raise PaymentConfigurationError("Webhook de paiement non configuré.")

    candidate = (signature or "").strip()
    if candidate.startswith("sha256="):
        candidate = candidate[7:]

    expected = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    if not candidate or not hmac.compare_digest(candidate.lower(), expected.lower()):
        raise InvalidPaymentSignature("Signature de paiement invalide.")


def _validate_provider_for_payment(user):
    if (
        not user.is_authenticated
        or not user.is_active
        or user.role != user.Role.PROVIDER
        or user.phone_verified_at is None
    ):
        raise PermissionDenied("Un prestataire actif avec téléphone vérifié est nécessaire.")

    try:
        provider = (
            ProviderProfile.objects.select_for_update()
            .select_related("user")
            .get(user=user, status=ProviderProfile.Status.VERIFIED)
        )
    except ProviderProfile.DoesNotExist as exc:
        raise PermissionDenied("Un prestataire vérifié est nécessaire.") from exc
    return provider


def _derive_purpose(provider, now):
    subscription = (
        ProviderSubscription.objects.select_for_update()
        .filter(
            provider=provider,
            status=ProviderSubscription.Status.ACTIVE,
            starts_at__lte=now,
            ends_at__gt=now,
        )
        .first()
    )
    return (
        PaymentTransaction.Purpose.RENEW
        if subscription is not None
        else PaymentTransaction.Purpose.ACTIVATE
    )


@transaction.atomic
def create_payment_transaction(user, *, plan_id, idempotency_key, payment_provider=None):
    provider = _validate_provider_for_payment(user)

    existing = (
        PaymentTransaction.objects.select_for_update()
        .filter(provider=provider, idempotency_key=idempotency_key)
        .first()
    )
    if existing is not None:
        if existing.plan_id != plan_id or (
            payment_provider and existing.payment_provider != payment_provider
        ):
            raise ValidationError(
                {"idempotency_key": "Cette clé a déjà été utilisée pour un autre plan."}
            )
        return existing, False

    try:
        plan = SubscriptionPlan.objects.select_for_update().get(
            pk=plan_id,
            is_active=True,
        )
    except SubscriptionPlan.DoesNotExist as exc:
        raise NotFound("Plan introuvable ou inactif.") from exc

    if plan.price_xof <= 0:
        raise ValidationError(
            {"plan_id": "Ce plan ne nécessite pas de paiement."}
        )

    now = timezone.now()
    transaction_obj = PaymentTransaction.objects.create(
        provider=provider,
        plan=plan,
        purpose=_derive_purpose(provider, now),
        payment_provider=payment_provider or settings.PAYMENT_PROVIDER,
        idempotency_key=idempotency_key,
        amount_xof=plan.price_xof,
        currency="XOF",
        plan_code_snapshot=plan.code,
        plan_name_snapshot=plan.name,
        duration_days_snapshot=plan.duration_days,
    )
    return transaction_obj, True


def _record_event(
    payment,
    *,
    fingerprint,
    reported_status,
    provider_transaction_id,
    amount_xof,
    currency,
    accepted,
    error_code="",
):
    try:
        event, created = PaymentWebhookEvent.objects.get_or_create(
            event_fingerprint=fingerprint,
            defaults={
                "transaction": payment,
                "reported_status": reported_status,
                "provider_transaction_id": provider_transaction_id,
                "amount_xof": amount_xof,
                "currency": currency,
                "accepted": accepted,
                "error_code": error_code,
            },
        )
    except IntegrityError:
        event = PaymentWebhookEvent.objects.get(event_fingerprint=fingerprint)
        created = False
    return event, created


def _attempt_fulfillment(payment):
    if payment.fulfilled_at is not None:
        return payment

    try:
        subscription = apply_paid_subscription(
            payment.provider_id,
            plan_id=payment.plan_id,
            duration_days=payment.duration_days_snapshot,
            payment_reference=payment.merchant_reference,
        )
    except Exception as exc:
        if isinstance(exc, (ValidationError, NotFound)):
            payment.fulfillment_error_code = "subscription_fulfillment_failed"
            payment.save(
                update_fields=["fulfillment_error_code", "updated_at"]
            )
            return payment
        raise

    payment.subscription = subscription
    payment.fulfilled_at = timezone.now()
    payment.fulfillment_error_code = ""
    payment.save(
        update_fields=[
            "subscription",
            "fulfilled_at",
            "fulfillment_error_code",
            "updated_at",
        ]
    )
    return payment


@transaction.atomic
def process_verified_webhook(payload, raw_body, *, expected_provider=None, checkout_session_id=None):
    fingerprint = hashlib.sha256(raw_body).hexdigest()

    try:
        payment = (
            PaymentTransaction.objects.select_for_update()
            .select_related("provider", "plan")
            .get(merchant_reference=payload["merchant_reference"])
        )
    except PaymentTransaction.DoesNotExist as exc:
        raise NotFound("Transaction de paiement introuvable.") from exc

    if expected_provider and payment.payment_provider != expected_provider:
        raise ValidationError({"detail": "Fournisseur de paiement incorrect."})
    if checkout_session_id and payment.checkout_session_id != checkout_session_id:
        raise ValidationError({"detail": "Session de paiement incorrecte."})

    existing_event = PaymentWebhookEvent.objects.filter(
        event_fingerprint=fingerprint
    ).first()
    if existing_event is not None:
        payment.refresh_from_db()
        if (
            payment.status == PaymentTransaction.Status.SUCCEEDED
            and payment.fulfilled_at is None
        ):
            _attempt_fulfillment(payment)
        return payment, "duplicate", 200

    if (
        payload["amount_xof"] != payment.amount_xof
        or payload["currency"].upper() != payment.currency
    ):
        _record_event(
            payment,
            fingerprint=fingerprint,
            reported_status=payload["status"],
            provider_transaction_id=payload["provider_transaction_id"],
            amount_xof=payload["amount_xof"],
            currency=payload["currency"].upper(),
            accepted=False,
            error_code="amount_or_currency_mismatch",
        )
        return payment, "rejected_amount", 400

    conflict = PaymentTransaction.objects.filter(
        provider_transaction_id=payload["provider_transaction_id"]
    ).exclude(pk=payment.pk).exists()
    if conflict:
        _record_event(
            payment,
            fingerprint=fingerprint,
            reported_status=payload["status"],
            provider_transaction_id=payload["provider_transaction_id"],
            amount_xof=payload["amount_xof"],
            currency=payload["currency"].upper(),
            accepted=False,
            error_code="provider_transaction_reused",
        )
        return payment, "rejected_provider_reference", 400

    mapped_status = {
        "SUCCESS": PaymentTransaction.Status.SUCCEEDED,
        "FAILED": PaymentTransaction.Status.FAILED,
        "CANCELLED": PaymentTransaction.Status.CANCELLED,
    }[payload["status"]]

    if payment.status in TERMINAL_STATUSES:
        accepted = payment.status == mapped_status
        _record_event(
            payment,
            fingerprint=fingerprint,
            reported_status=payload["status"],
            provider_transaction_id=payload["provider_transaction_id"],
            amount_xof=payload["amount_xof"],
            currency=payload["currency"].upper(),
            accepted=accepted,
            error_code="" if accepted else "terminal_status_conflict",
        )
        if (
            payment.status == PaymentTransaction.Status.SUCCEEDED
            and payment.fulfilled_at is None
        ):
            _attempt_fulfillment(payment)
        return payment, "terminal", 200

    payment.status = mapped_status
    payment.provider_transaction_id = payload["provider_transaction_id"]
    if mapped_status == PaymentTransaction.Status.SUCCEEDED:
        payment.confirmed_at = timezone.now()
    payment.save(
        update_fields=[
            "status",
            "provider_transaction_id",
            "confirmed_at",
            "updated_at",
        ]
    )

    _record_event(
        payment,
        fingerprint=fingerprint,
        reported_status=payload["status"],
        provider_transaction_id=payload["provider_transaction_id"],
        amount_xof=payload["amount_xof"],
        currency=payload["currency"].upper(),
        accepted=True,
    )

    if mapped_status == PaymentTransaction.Status.SUCCEEDED:
        _attempt_fulfillment(payment)

    return payment, "processed", 200


@transaction.atomic
def retry_fulfillment(payment_id, actor):
    if not can_manage_payments(actor):
        raise PermissionDenied("Gestion des paiements non autorisée.")

    try:
        payment = PaymentTransaction.objects.select_for_update().get(
            pk=payment_id
        )
    except PaymentTransaction.DoesNotExist as exc:
        raise NotFound("Transaction de paiement introuvable.") from exc

    if payment.status != PaymentTransaction.Status.SUCCEEDED:
        raise ValidationError(
            {"detail": "Seul un paiement réussi peut être retraité."}
        )
    if payment.fulfilled_at is not None:
        return payment
    return _attempt_fulfillment(payment)
