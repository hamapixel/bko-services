"""Orange Money Web Payment integration for BKO Services.

The browser redirect is never trusted. Orange's notification token only identifies
an existing checkout; BKO then queries Orange's transaction-status endpoint and
fulfills the subscription from that server-to-server result.
"""

import base64
import hashlib
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
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


ORANGE_TOKEN_URL = "https://api.orange.com/oauth/v3/token"
_ALLOWED_COUNTRIES = {"dev", "ml"}


class OrangeMoneyUnavailable(APIException):
    status_code = 502
    default_detail = (
        "Orange Money est temporairement indisponible. "
        "Aucun abonnement n'a été activé."
    )


class InvalidOrangeMoneyNotification(Exception):
    pass


def _env(name, default=""):
    return os.getenv(name, default).strip()


def _timeout():
    try:
        return max(1, int(_env("ORANGE_MONEY_HTTP_TIMEOUT_SECONDS", "8")))
    except ValueError:
        return 8


def _country():
    return _env("ORANGE_MONEY_COUNTRY", "dev").lower()


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


def orange_money_is_configured():
    return bool(
        _env("ORANGE_MONEY_CLIENT_ID")
        and _env("ORANGE_MONEY_CLIENT_SECRET")
        and _env("ORANGE_MONEY_MERCHANT_KEY")
        and _country() in _ALLOWED_COUNTRIES
        and _public_origin_is_valid()
    )


def _read_json(request):
    try:
        with urlopen(request, timeout=_timeout()) as response:
            body = response.read(65536).decode("utf-8")
        parsed = json.loads(body)
    except (HTTPError, URLError, TimeoutError, UnicodeDecodeError, ValueError) as exc:
        raise OrangeMoneyUnavailable() from exc
    if not isinstance(parsed, dict):
        raise OrangeMoneyUnavailable()
    return parsed


def _oauth_token():
    client_id = _env("ORANGE_MONEY_CLIENT_ID")
    client_secret = _env("ORANGE_MONEY_CLIENT_SECRET")
    credentials = base64.b64encode(
        f"{client_id}:{client_secret}".encode("utf-8")
    ).decode("ascii")
    request = Request(
        ORANGE_TOKEN_URL,
        data=urlencode({"grant_type": "client_credentials"}).encode("ascii"),
        method="POST",
        headers={
            "Authorization": "Basic " + credentials,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
    )
    result = _read_json(request)
    token = result.get("access_token")
    if not isinstance(token, str) or not token:
        raise OrangeMoneyUnavailable()
    return token


def _orange_request(resource, payload):
    country = _country()
    if country not in _ALLOWED_COUNTRIES:
        raise PaymentConfigurationError("Pays Orange Money non configuré.")
    if resource not in {"webpayment", "transactionstatus"}:
        raise OrangeMoneyUnavailable()

    token = _oauth_token()
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = Request(
        f"https://api.orange.com/orange-money-webpay/{country}/v1/{resource}",
        data=raw,
        method="POST",
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    return _read_json(request)


def _order_id(payment):
    # Orange limits order_id to 30 characters.
    return "BKO" + payment.pk.hex.upper()[:27]


def _notification_fingerprint(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:40]


def _checkout_url_is_valid(value, pay_token):
    if not isinstance(value, str) or not value:
        return False
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    parts = [part for part in parsed.path.split("/") if part]
    return bool(
        parsed.scheme == "https"
        and (host == "orange-money.com" or host.endswith(".orange-money.com"))
        and not parsed.username
        and not parsed.password
        and parts
        and parts[-1] == pay_token
    )


def _pay_token_from_checkout(payment):
    parsed = urlparse(payment.checkout_url)
    parts = [part for part in parsed.path.split("/") if part]
    if not parts:
        raise ValidationError({"detail": "Jeton Orange Money introuvable."})
    token = parts[-1]
    if not token or len(token) > 256:
        raise ValidationError({"detail": "Jeton Orange Money invalide."})
    return token


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
    return_base = origin + "/prestataire/abonnement?transaction=" + str(payment.pk)
    notify_url = origin + "/api/v1/payments/webhooks/orange-money/"
    result = _orange_request(
        "webpayment",
        {
            "merchant_key": _env("ORANGE_MONEY_MERCHANT_KEY"),
            "currency": "OUV" if _country() == "dev" else "XOF",
            "order_id": _order_id(payment),
            "amount": payment.amount_xof,
            "return_url": return_base + "&paiement=retour",
            "cancel_url": return_base + "&paiement=erreur",
            "notif_url": notify_url,
            "lang": "fr",
            "reference": ("BKO " + payment.plan_code_snapshot)[:30],
        },
    )

    if str(result.get("status")) != "201":
        raise OrangeMoneyUnavailable()
    pay_token = result.get("pay_token")
    checkout_url = result.get("payment_url")
    notif_token = result.get("notif_token")
    if (
        not isinstance(pay_token, str)
        or not pay_token
        or not isinstance(notif_token, str)
        or not notif_token
        or not _checkout_url_is_valid(checkout_url, pay_token)
    ):
        raise OrangeMoneyUnavailable()

    payment.checkout_session_id = _notification_fingerprint(notif_token)
    payment.checkout_url = checkout_url
    payment.save(update_fields=["checkout_session_id", "checkout_url", "updated_at"])
    return payment


def start_orange_money_payment(user, *, plan_id, idempotency_key):
    if not orange_money_is_configured():
        raise PaymentConfigurationError("Orange Money n'est pas encore configuré.")
    payment, _ = create_payment_transaction(
        user,
        plan_id=plan_id,
        idempotency_key=idempotency_key,
        payment_provider="ORANGE_MONEY",
    )
    return _prepare_checkout(payment.pk)


def _verified_status(payment):
    result = _orange_request(
        "transactionstatus",
        {
            "order_id": _order_id(payment),
            "amount": payment.amount_xof,
            "pay_token": _pay_token_from_checkout(payment),
        },
    )
    if str(result.get("order_id", "")) != _order_id(payment):
        raise ValidationError({"detail": "Référence Orange Money incohérente."})
    return result


def complete_orange_money_checkout(notification_payload):
    notif_token = str(notification_payload.get("notif_token", "")).strip()
    if not notif_token:
        raise InvalidOrangeMoneyNotification("Token Orange Money absent.")

    fingerprint = _notification_fingerprint(notif_token)
    try:
        payment = PaymentTransaction.objects.get(
            checkout_session_id=fingerprint,
            payment_provider="ORANGE_MONEY",
        )
    except PaymentTransaction.DoesNotExist as exc:
        raise InvalidOrangeMoneyNotification("Token Orange Money invalide.") from exc

    if payment.status == PaymentTransaction.Status.SUCCEEDED and payment.fulfilled_at:
        return payment, "duplicate", 200

    verified = _verified_status(payment)
    status_value = str(verified.get("status", "")).upper()

    if status_value in {"INITIATED", "PENDING"}:
        return payment, "waiting", 200
    if status_value not in {"SUCCESS", "FAILED", "EXPIRED"}:
        raise ValidationError({"detail": "Statut Orange Money invalide."})

    mapped = {
        "SUCCESS": "SUCCESS",
        "FAILED": "FAILED",
        "EXPIRED": "CANCELLED",
    }[status_value]
    txnid = str(verified.get("txnid") or "").strip()
    provider_transaction_id = txnid or f"ORANGE-{payment.pk.hex.upper()}-{status_value}"

    canonical = json.dumps(
        {
            "order_id": _order_id(payment),
            "status": status_value,
            "txnid": txnid,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return process_verified_webhook(
        {
            "merchant_reference": payment.merchant_reference,
            "provider_transaction_id": provider_transaction_id,
            "status": mapped,
            "amount_xof": payment.amount_xof,
            "currency": "XOF",
        },
        canonical,
        expected_provider="ORANGE_MONEY",
        checkout_session_id=fingerprint,
    )
