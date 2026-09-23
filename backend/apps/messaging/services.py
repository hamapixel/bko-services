import hashlib
import hmac
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import Throttled

from .models import SmsDeliveryLog


def hash_request_ip(remote_addr):
    if not remote_addr:
        return ""
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        remote_addr.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def enforce_shared_otp_ip_limit(remote_addr):
    ip_hash = hash_request_ip(remote_addr)
    if not ip_hash:
        return ""

    since = timezone.now() - timedelta(hours=1)
    count = SmsDeliveryLog.objects.filter(
        request_ip_hash=ip_hash,
        created_at__gte=since,
        purpose=SmsDeliveryLog.Purpose.PHONE_VERIFICATION,
    ).count()
    if count >= settings.SMS_OTP_IP_LIMIT_PER_HOUR:
        raise Throttled(
            detail="Trop de demandes de code depuis cette connexion. Réessayez plus tard."
        )
    return ip_hash


@transaction.atomic
def create_sms_delivery_log(*, user, recipient, provider, request_ip_hash):
    return SmsDeliveryLog.objects.create(
        user=user,
        recipient=recipient,
        purpose=SmsDeliveryLog.Purpose.PHONE_VERIFICATION,
        provider=provider,
        request_ip_hash=request_ip_hash,
    )


@transaction.atomic
def mark_sms_accepted(log_id, result):
    log = SmsDeliveryLog.objects.select_for_update().get(pk=log_id)
    message_id = getattr(result, "message_id", "")
    provider_status = getattr(result, "provider_status", "")
    log.status = SmsDeliveryLog.Status.ACCEPTED
    log.provider_message_id = message_id if isinstance(message_id, str) else ""
    log.provider_status = provider_status if isinstance(provider_status, str) else ""
    log.error_code = ""
    log.accepted_at = timezone.now()
    log.save(
        update_fields=[
            "status",
            "provider_message_id",
            "provider_status",
            "error_code",
            "accepted_at",
        ]
    )


@transaction.atomic
def mark_sms_failed(log_id, error_code):
    log = SmsDeliveryLog.objects.select_for_update().get(pk=log_id)
    log.status = SmsDeliveryLog.Status.FAILED
    log.error_code = (error_code or "sms_delivery_failed")[:64]
    log.save(update_fields=["status", "error_code"])
