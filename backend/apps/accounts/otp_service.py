from django.conf import settings
import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import Throttled, ValidationError

from apps.messaging.providers import DeliveryUnavailable, SmsDeliveryError, get_sms_provider
from apps.messaging.services import (
    create_sms_delivery_log,
    enforce_shared_otp_ip_limit,
    mark_sms_accepted,
    mark_sms_failed,
)

from .models import OtpCode


def request_verification_code(user, host: str, remote_addr: str) -> None:
    provider = get_sms_provider(host, remote_addr)
    now = timezone.now()

    with transaction.atomic():
        locked_user = get_user_model().objects.select_for_update().get(pk=user.pk)
        if locked_user.phone_verified_at is not None:
            raise ValidationError({"detail": "Ce numéro est déjà vérifié."})

        request_ip_hash = enforce_shared_otp_ip_limit(remote_addr)

        recent = OtpCode.objects.filter(
            user=locked_user,
            created_at__gte=now - timedelta(hours=24),
        )
        if recent.count() >= settings.OTP_PHONE_DAILY_LIMIT:
            raise Throttled(detail="Limite quotidienne de codes atteinte.")

        latest = recent.order_by("-created_at").first()
        if latest and latest.created_at + timedelta(seconds=settings.OTP_MIN_REQUEST_INTERVAL_SECONDS) > now:
            raise Throttled(
                wait=settings.OTP_MIN_REQUEST_INTERVAL_SECONDS,
                detail="Attendez avant de demander un autre code.",
            )

        code = f"{secrets.randbelow(1_000_000):06d}"
        OtpCode.objects.filter(
            user=locked_user,
            consumed_at__isnull=True,
        ).update(consumed_at=now)
        otp = OtpCode.objects.create(
            user=locked_user,
            code_hash=make_password(code),
            expires_at=now + timedelta(seconds=settings.OTP_CODE_TTL_SECONDS),
        )
        delivery_log = create_sms_delivery_log(
            user=locked_user,
            recipient=locked_user.phone,
            provider=provider.provider_name,
            request_ip_hash=request_ip_hash,
        )

    try:
        result = provider.send_sms(
            locked_user.phone,
            f"Votre code BKO Services : {code}. Il expire dans 5 minutes.",
        )
    except SmsDeliveryError as exc:
        failure_time = timezone.now()
        with transaction.atomic():
            OtpCode.objects.filter(
                pk=otp.pk,
                consumed_at__isnull=True,
            ).update(consumed_at=failure_time)
            mark_sms_failed(delivery_log.pk, exc.code)
        raise DeliveryUnavailable("Le fournisseur SMS n'a pas accepté le message.") from exc

    mark_sms_accepted(delivery_log.pk, result)


@transaction.atomic
def verify_phone_code(user, code: str) -> bool:
    locked_user = get_user_model().objects.select_for_update().get(pk=user.pk)
    if locked_user.phone_verified_at is not None:
        raise ValidationError({"detail": "Ce numéro est déjà vérifié."})

    otp = (
        OtpCode.objects.select_for_update()
        .filter(user=locked_user, consumed_at__isnull=True)
        .order_by("-created_at")
        .first()
    )
    now = timezone.now()
    if otp is None or otp.expires_at <= now:
        raise ValidationError({"code": "Code absent ou expiré."})
    if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise Throttled(detail="Trop de tentatives pour ce code.")

    otp.attempts += 1
    if not check_password(code, otp.code_hash):
        otp.save(update_fields=["attempts"])
        return False

    otp.consumed_at = now
    otp.save(update_fields=["attempts", "consumed_at"])
    locked_user.phone_verified_at = now
    locked_user.save(update_fields=["phone_verified_at"])
    return True
