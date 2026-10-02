"""CinetPay hosted checkout integration for BKO Services.

CinetPay notifies BKO, then BKO independently checks the transaction with
CinetPay before activating or renewing any subscription. Browser return URLs
never confirm a payment.
"""

import hashlib
import hmac
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import APIException, ValidationError

from .models import PaymentTransaction
from .services import PaymentConfigurationError, create_payment_transaction, process_verified_webhook


CINETPAY_INIT_URL = "https://api-checkout.cinetpay.com/v2/payment"
CINETPAY_CHECK_URL = "https://api-checkout.cinetpay.com/v2/payment/check"


class CinetPayUnavailable(APIException):
    status_code = 502
    default_detail = (
        "CinetPay est temporairement indisponible. Aucun abonnement n'a été activé."
    )


class InvalidCinetPayToken(Exception):
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


def cinetpay_is_configured():
    return bool(
        settings.CINETPAY_API_KEY
        and settings.CINETPAY_SITE_ID
        and settings.CINETPAY_SECRET_KEY
        and _public_origin_is_valid()
    )


def _cinetpay_request(url, payload):
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = Request(
        url,
        data=raw,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urlopen(
            request,
            timeout=settings.CINETPAY_HTTP_TIMEOUT_SECONDS,
        ) as response:
            body = response.read(65536).decode("utf-8")
        parsed = json.loads(body)
    except (HTTPError, URLError, TimeoutError, UnicodeDecodeError, ValueError) as exc:
        raise CinetPayUnavailable() from exc
    if not isinstance(parsed, dict):
        raise CinetPayUnavailable()
    return parsed


def _transaction_id(payment):
    # CinetPay recommends a unique identifier without special characters.
    return payment.pk.hex.upper()


def _checkout_url_is_valid(value):
    if not isinstance(value, str) or not value:
        return False
    parsed = urlparse(value)
    return bool(
        parsed.scheme == "https"
        and parsed.hostname == "checkout.cinetpay.com"
        and not parsed.username
        and not parsed.password
    )


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
    if payment.amount_xof <= 0 or payment.amount_xof % 5 != 0:
        raise ValidationError(
            {"detail": "Le montant CinetPay doit être positif et multiple de 5 FCFA."}
        )

    transaction_id = payment.checkout_session_id or _transaction_id(payment)
    origin = settings.PAYMENT_RETURN_ORIGIN
    return_url = (
        origin
        + "/prestataire/abonnement?transaction="
        + str(payment.pk)
        + "&paiement=retour"
    )
    notify_url = origin + "/api/v1/payments/webhooks/cinetpay/"

    result = _cinetpay_request(
        CINETPAY_INIT_URL,
        {
            "apikey": settings.CINETPAY_API_KEY,
            "site_id": settings.CINETPAY_SITE_ID,
            "transaction_id": transaction_id,
            "amount": payment.amount_xof,
            "currency": "XOF",
            "description": "Abonnement BKO Services",
            "notify_url": notify_url,
            "return_url": return_url,
            "channels": settings.CINETPAY_CHANNELS,
            "lang": "fr",
            "metadata": payment.merchant_reference,
            "customer_id": str(payment.provider_id),
            "customer_phone_number": payment.provider.user.phone,
        },
    )
    if str(result.get("code")) != "201":
        raise CinetPayUnavailable()
    data = result.get("data")
    if not isinstance(data, dict):
        raise CinetPayUnavailable()
    checkout_url = data.get("payment_url")
    if not _checkout_url_is_valid(checkout_url):
        raise CinetPayUnavailable()

    payment.checkout_session_id = transaction_id
    payment.checkout_url = checkout_url
    payment.save(update_fields=["checkout_session_id", "checkout_url", "updated_at"])
    return payment


def start_cinetpay_payment(user, *, plan_id, idempotency_key):
    if not cinetpay_is_configured():
        raise PaymentConfigurationError("CinetPay n'est pas encore configuré.")
    payment, _ = create_payment_transaction(
        user,
        plan_id=plan_id,
        idempotency_key=idempotency_key,
        payment_provider="CINETPAY",
    )
    return _prepare_checkout(payment.pk)


_HMAC_FIELDS = (
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


def verify_cinetpay_token(payload, received_token):
    if not settings.CINETPAY_SECRET_KEY:
        raise PaymentConfigurationError("Secret HMAC CinetPay non configuré.")
    if str(payload.get("cpm_site_id", "")) != str(settings.CINETPAY_SITE_ID):
        raise InvalidCinetPayToken("Site CinetPay invalide.")
    candidate = (received_token or "").strip().lower()
    message = "".join(str(payload.get(field, "") or "") for field in _HMAC_FIELDS)
    expected = hmac.new(
        settings.CINETPAY_SECRET_KEY.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not candidate or not hmac.compare_digest(candidate, expected.lower()):
        raise InvalidCinetPayToken("Token CinetPay invalide.")


def _verified_status_payload(transaction_id):
    result = _cinetpay_request(
        CINETPAY_CHECK_URL,
        {
            "apikey": settings.CINETPAY_API_KEY,
            "site_id": settings.CINETPAY_SITE_ID,
            "transaction_id": transaction_id,
        },
    )
    data = result.get("data")
    if not isinstance(data, dict):
        raise CinetPayUnavailable()
    return result, data


def complete_cinetpay_checkout(notification_payload):
    transaction_id = str(notification_payload.get("cpm_trans_id", "")).strip()
    if not transaction_id:
        raise ValidationError({"detail": "Référence CinetPay absente."})

    try:
        payment = PaymentTransaction.objects.get(
            checkout_session_id=transaction_id,
            payment_provider="CINETPAY",
        )
    except PaymentTransaction.DoesNotExist as exc:
        raise ValidationError({"detail": "Transaction CinetPay inconnue."}) from exc

    if payment.status == PaymentTransaction.Status.SUCCEEDED and payment.fulfilled_at:
        return payment, "duplicate", 200

    verified_response, verified = _verified_status_payload(transaction_id)
    status_value = str(verified.get("status", "")).upper()

    # Waiting states must remain pending. CinetPay can notify more than once.
    if status_value not in {"ACCEPTED", "REFUSED", "CANCELLED"}:
        return payment, "waiting", 200

    try:
        amount_xof = int(str(verified.get("amount", "")))
    except (TypeError, ValueError) as exc:
        raise ValidationError({"detail": "Montant CinetPay invalide."}) from exc

    mapped = {
        "ACCEPTED": "SUCCESS",
        "REFUSED": "FAILED",
        "CANCELLED": "CANCELLED",
    }[status_value]
    operator_id = str(verified.get("operator_id") or "").strip()
    provider_transaction_id = operator_id or f"CINETPAY-{transaction_id}"

    # Fingerprint the independently verified CinetPay result, not browser-return data.
    canonical = json.dumps(
        {
            "transaction_id": transaction_id,
            "code": str(verified_response.get("code", "")),
            "status": status_value,
            "amount": amount_xof,
            "currency": str(verified.get("currency", "")).upper(),
            "operator_id": operator_id,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return process_verified_webhook(
        {
            "merchant_reference": payment.merchant_reference,
            "provider_transaction_id": provider_transaction_id,
            "status": mapped,
            "amount_xof": amount_xof,
            "currency": str(verified.get("currency", "")).upper(),
        },
        canonical,
        expected_provider="CINETPAY",
        checkout_session_id=transaction_id,
    )
