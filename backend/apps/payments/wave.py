"""Wave hosted checkout. Secrets and payment confirmation stay on the server."""

import hashlib
import hmac
import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import APIException, ValidationError

from .models import PaymentTransaction
from .services import (
    InvalidPaymentSignature,
    PaymentConfigurationError,
    create_payment_transaction,
    process_verified_webhook,
)


class WaveUnavailable(APIException):
    status_code = 502
    default_detail = "Wave est temporairement indisponible. Aucun abonnement n'a été activé."


def wave_is_configured():
    origin = urlparse(settings.PAYMENT_RETURN_ORIGIN)
    return bool(
        settings.WAVE_API_KEY
        and settings.WAVE_WEBHOOK_SECRET
        and origin.scheme == "https"
        and origin.netloc
        and not origin.username
        and not origin.password
        and not origin.path
        and not origin.query
        and not origin.fragment
    )


def _wave_request(method, path, payload=None):
    raw = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        "https://api.wave.com" + path,
        data=raw,
        method=method,
        headers={
            "Authorization": "Bearer " + settings.WAVE_API_KEY,
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=8) as response:
            return json.loads(response.read(65536).decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise WaveUnavailable() from exc


def _session_matches(payment, session):
    try:
        amount = int(session["amount"])
    except (KeyError, TypeError, ValueError):
        return False
    return (
        session.get("client_reference") == payment.merchant_reference
        and amount == payment.amount_xof
        and session.get("currency") == "XOF"
        and isinstance(session.get("id"), str)
        and session["id"].startswith("cos-")
    )


@transaction.atomic
def _checkout_for_payment(payment_id):
    # Serialize duplicate clicks on the same transaction. Search Wave first, so a
    # timed-out response cannot create a second payable session on retry.
    payment = PaymentTransaction.objects.select_for_update().get(pk=payment_id)
    if payment.checkout_url:
        return payment
    if payment.status != PaymentTransaction.Status.PENDING:
        return payment
    search = _wave_request(
        "GET",
        "/v1/checkout/sessions/search?client_reference="
        + quote(payment.merchant_reference, safe=""),
    )
    sessions = search.get("result", [])
    if not isinstance(sessions, list):
        raise WaveUnavailable()
    session = next((item for item in sessions if _session_matches(payment, item)), None)
    if session is None:
        origin = settings.PAYMENT_RETURN_ORIGIN
        return_url = origin + "/prestataire/abonnement?transaction=" + str(payment.pk)
        session = _wave_request(
            "POST",
            "/v1/checkout/sessions",
            {
                "amount": str(payment.amount_xof),
                "currency": "XOF",
                "client_reference": payment.merchant_reference,
                "success_url": return_url + "&paiement=retour",
                "error_url": return_url + "&paiement=erreur",
            },
        )
    if not _session_matches(payment, session):
        raise WaveUnavailable()
    url = session.get("wave_launch_url", "")
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "pay.wave.com" or parsed.username:
        raise WaveUnavailable()
    payment.checkout_session_id = session["id"]
    payment.checkout_url = url
    payment.save(update_fields=["checkout_session_id", "checkout_url", "updated_at"])
    return payment


def start_wave_payment(user, *, plan_id, idempotency_key):
    if not wave_is_configured():
        raise PaymentConfigurationError("Wave n'est pas encore configuré.")
    payment, _ = create_payment_transaction(
        user, plan_id=plan_id, idempotency_key=idempotency_key, payment_provider="WAVE"
    )
    return _checkout_for_payment(payment.pk)


def verify_wave_signature(raw_body, signature):
    if not settings.WAVE_WEBHOOK_SECRET:
        raise PaymentConfigurationError("Webhook Wave non configuré.")
    parts = [part.strip().split("=", 1) for part in signature.split(",") if "=" in part]
    timestamps = [value for key, value in parts if key == "t"]
    signatures = [value for key, value in parts if key == "v1"]
    if len(timestamps) != 1 or not timestamps[0].isdigit() or not signatures:
        raise InvalidPaymentSignature("Signature Wave invalide.")
    timestamp = timestamps[0]
    if abs(time.time() - int(timestamp)) > 300:
        raise InvalidPaymentSignature("Signature Wave expirée.")
    expected = hmac.new(
        settings.WAVE_WEBHOOK_SECRET.encode("utf-8"),
        timestamp.encode("ascii") + raw_body,
        hashlib.sha256,
    ).hexdigest()
    if not any(hmac.compare_digest(expected, candidate) for candidate in signatures):
        raise InvalidPaymentSignature("Signature Wave invalide.")


def complete_wave_checkout(payload, raw_body):
    if payload.get("type") != "checkout.session.completed":
        return None
    session = payload.get("data")
    if not isinstance(session, dict) or (
        session.get("payment_status") != "succeeded"
        or session.get("checkout_status") != "complete"
    ):
        raise ValidationError({"detail": "Paiement Wave non confirmé."})
    reference = session.get("client_reference")
    session_id = session.get("id")
    transaction_id = session.get("transaction_id")
    amount = session.get("amount")
    if not all(isinstance(x, str) and x for x in (reference, session_id, transaction_id)):
        raise ValidationError({"detail": "Références Wave incomplètes."})
    if not isinstance(amount, str) or not amount.isdigit():
        raise ValidationError({"detail": "Montant Wave invalide."})
    return process_verified_webhook(
        {
            "merchant_reference": reference,
            "provider_transaction_id": transaction_id,
            "status": "SUCCESS",
            "amount_xof": int(amount),
            "currency": session.get("currency", ""),
        },
        raw_body,
        expected_provider="WAVE",
        checkout_session_id=session_id,
    )
