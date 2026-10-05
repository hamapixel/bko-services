"""PayDunya hosted checkout integration for BKO Services.

The browser return never confirms a payment. BKO authenticates PayDunya's IPN,
then independently checks the invoice server-to-server before subscription
fulfillment.
"""

import hashlib
import hmac
import json
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import APIException, ValidationError

from .models import PaymentTransaction
from .services import (
    PaymentConfigurationError,
    create_payment_transaction,
    process_verified_webhook,
)

_ALLOWED_MODES = {"sandbox", "live"}
_ALLOWED_MALI_CHANNELS = {"orange-money-mali"}


class PayDunyaUnavailable(APIException):
    status_code = 502
    default_detail = (
        "PayDunya est temporairement indisponible. "
        "Aucun abonnement n'a été activé."
    )


class InvalidPayDunyaNotification(Exception):
    pass


def _public_origin_is_valid():
    origin = urlparse(settings.PAYMENT_RETURN_ORIGIN)
    return bool(
        origin.scheme == "https"
        and origin.netloc
        and not origin.username
        and not origin.password
        and not origin.path
        and not origin.query
        and not origin.fragment
    )


def _mode():
    return str(settings.PAYDUNYA_MODE or "sandbox").strip().lower()


def _channels():
    values = [
        item.strip()
        for item in str(settings.PAYDUNYA_CHANNELS or "").split(",")
        if item.strip()
    ]
    return values or ["orange-money-mali"]


def paydunya_is_configured():
    channels = _channels()
    return bool(
        settings.PAYDUNYA_MASTER_KEY
        and settings.PAYDUNYA_PRIVATE_KEY
        and settings.PAYDUNYA_TOKEN
        and _mode() in _ALLOWED_MODES
        and channels
        and set(channels).issubset(_ALLOWED_MALI_CHANNELS)
        and _public_origin_is_valid()
    )


def _api_base():
    if _mode() == "sandbox":
        return "https://app.paydunya.com/sandbox-api/v1"
    if _mode() == "live":
        return "https://app.paydunya.com/api/v1"
    raise PaymentConfigurationError("Mode PayDunya invalide.")


def _headers():
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "PAYDUNYA-MASTER-KEY": settings.PAYDUNYA_MASTER_KEY,
        "PAYDUNYA-PRIVATE-KEY": settings.PAYDUNYA_PRIVATE_KEY,
        "PAYDUNYA-TOKEN": settings.PAYDUNYA_TOKEN,
    }


def _paydunya_request(method, path, payload=None):
    data = None
    if payload is not None:
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = Request(_api_base() + path, data=data, method=method, headers=_headers())
    try:
        with urlopen(request, timeout=settings.PAYDUNYA_HTTP_TIMEOUT_SECONDS) as response:
            body = response.read(65536).decode("utf-8")
        parsed = json.loads(body)
    except (HTTPError, URLError, TimeoutError, UnicodeDecodeError, ValueError) as exc:
        raise PayDunyaUnavailable() from exc
    if not isinstance(parsed, dict):
        raise PayDunyaUnavailable()
    return parsed


def _token_fingerprint(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:40]


def _checkout_url_is_valid(value, token):
    if not isinstance(value, str) or not value:
        return False
    parsed = urlparse(value)
    parts = [part for part in parsed.path.split("/") if part]
    return bool(
        parsed.scheme == "https"
        and parsed.hostname == "app.paydunya.com"
        and not parsed.username
        and not parsed.password
        and parts
        and parts[-1] == token
    )


def _token_from_checkout(payment):
    parsed = urlparse(payment.checkout_url)
    parts = [part for part in parsed.path.split("/") if part]
    if not parts:
        raise ValidationError({"detail": "Token PayDunya introuvable."})
    token = parts[-1]
    if not token or len(token) > 256:
        raise ValidationError({"detail": "Token PayDunya invalide."})
    return token


def find_paydunya_payment_by_token(token):
    token = str(token or "").strip()
    if not token or len(token) > 256:
        raise InvalidPayDunyaNotification("Token PayDunya invalide.")
    try:
        return PaymentTransaction.objects.get(
            checkout_session_id=_token_fingerprint(token),
            payment_provider="PAYDUNYA",
        )
    except PaymentTransaction.DoesNotExist as exc:
        raise InvalidPayDunyaNotification("Transaction PayDunya inconnue.") from exc


@transaction.atomic
def _prepare_checkout(payment_id):
    payment = (
        PaymentTransaction.objects.select_for_update()
        .select_related("plan", "provider__user")
        .get(pk=payment_id)
    )
    if payment.checkout_url:
        return payment
    if payment.status != PaymentTransaction.Status.PENDING:
        return payment

    origin = settings.PAYMENT_RETURN_ORIGIN
    result = _paydunya_request(
        "POST",
        "/checkout-invoice/create",
        {
            "invoice": {
                "total_amount": payment.amount_xof,
                "description": (
                    "Abonnement BKO Services - " + payment.plan_name_snapshot
                )[:200],
                "channels": _channels(),
                "customer": {
                    "name": payment.provider.display_name,
                    "phone": payment.provider.user.phone,
                },
            },
            "store": {"name": "BKO Services"},
            "custom_data": {
                "merchant_reference": payment.merchant_reference,
                "payment_id": str(payment.pk),
            },
            "actions": {
                "cancel_url": origin + "/prestataire/abonnement?paiement=erreur",
                "return_url": origin + "/api/v1/payments/returns/paydunya/",
                "callback_url": origin + "/api/v1/payments/webhooks/paydunya/",
            },
        },
    )
    if str(result.get("response_code")) != "00":
        raise PayDunyaUnavailable()

    token = str(result.get("token") or "").strip()
    checkout_url = result.get("response_text")
    if not token or len(token) > 256 or not _checkout_url_is_valid(checkout_url, token):
        raise PayDunyaUnavailable()

    payment.checkout_session_id = _token_fingerprint(token)
    payment.checkout_url = checkout_url
    payment.save(update_fields=["checkout_session_id", "checkout_url", "updated_at"])
    return payment


def start_paydunya_payment(user, *, plan_id, idempotency_key):
    if not paydunya_is_configured():
        raise PaymentConfigurationError("PayDunya n'est pas encore configuré.")
    payment, _ = create_payment_transaction(
        user,
        plan_id=plan_id,
        idempotency_key=idempotency_key,
        payment_provider="PAYDUNYA",
    )
    return _prepare_checkout(payment.pk)


def _expected_hash():
    return hashlib.sha512(settings.PAYDUNYA_MASTER_KEY.encode("utf-8")).hexdigest()


def _verify_hash(value):
    candidate = str(value or "").strip().lower()
    if not candidate or not hmac.compare_digest(candidate, _expected_hash().lower()):
        raise InvalidPayDunyaNotification("Hash PayDunya invalide.")


def _callback_identity(payload):
    if not hasattr(payload, "get"):
        raise InvalidPayDunyaNotification("Notification PayDunya invalide.")
    nested = payload.get("data")
    if isinstance(nested, str):
        try:
            nested = json.loads(nested)
        except (TypeError, ValueError):
            nested = None
    if isinstance(nested, dict):
        invoice = nested.get("invoice")
        invoice = invoice if isinstance(invoice, dict) else {}
        return nested.get("hash"), invoice.get("token") or nested.get("token")
    return (
        payload.get("data[hash]") or payload.get("hash"),
        payload.get("data[invoice][token]")
        or payload.get("data[token]")
        or payload.get("token"),
    )


def _confirmed_invoice(token):
    result = _paydunya_request("GET", "/checkout-invoice/confirm/" + token)
    if str(result.get("response_code")) != "00":
        raise PayDunyaUnavailable()
    _verify_hash(result.get("hash"))
    invoice = result.get("invoice")
    if not isinstance(invoice, dict):
        raise ValidationError({"detail": "Facture PayDunya invalide."})
    if str(invoice.get("token") or "").strip() != token:
        raise ValidationError({"detail": "Token PayDunya incohérent."})
    return result


def _integer_amount(value):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValidationError({"detail": "Montant PayDunya invalide."}) from exc
    if amount != amount.to_integral_value() or amount < 0:
        raise ValidationError({"detail": "Montant PayDunya invalide."})
    return int(amount)


def complete_paydunya_checkout(notification_payload):
    callback_hash, token = _callback_identity(notification_payload)
    _verify_hash(callback_hash)
    payment = find_paydunya_payment_by_token(token)
    if payment.status == PaymentTransaction.Status.SUCCEEDED and payment.fulfilled_at:
        return payment, "duplicate", 200

    token = _token_from_checkout(payment)
    confirmed = _confirmed_invoice(token)
    status_value = str(confirmed.get("status") or "").strip().lower()
    if status_value == "pending":
        return payment, "waiting", 200
    if status_value not in {"completed", "failed", "cancelled"}:
        raise ValidationError({"detail": "Statut PayDunya invalide."})

    invoice = confirmed.get("invoice") or {}
    amount_xof = _integer_amount(invoice.get("total_amount"))
    custom_data = confirmed.get("custom_data")
    custom_data = custom_data if isinstance(custom_data, dict) else {}
    if str(custom_data.get("merchant_reference") or "") != payment.merchant_reference:
        raise ValidationError({"detail": "Référence PayDunya incohérente."})

    mapped = {
        "completed": "SUCCESS",
        "failed": "FAILED",
        "cancelled": "CANCELLED",
    }[status_value]
    canonical = json.dumps(
        {
            "token": token,
            "status": status_value,
            "amount_xof": amount_xof,
            "merchant_reference": payment.merchant_reference,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return process_verified_webhook(
        {
            "merchant_reference": payment.merchant_reference,
            "provider_transaction_id": "PAYDUNYA-" + _token_fingerprint(token),
            "status": mapped,
            "amount_xof": amount_xof,
            "currency": "XOF",
        },
        canonical,
        expected_provider="PAYDUNYA",
        checkout_session_id=_token_fingerprint(token),
    )
