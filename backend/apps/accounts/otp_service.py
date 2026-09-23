import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import Throttled, ValidationError

from .models import OtpCode
from .otp_delivery import get_sms_provider


@transaction.atomic
def request_verification_code(user, host: str, remote_addr: str) -> None:
    locked_user = get_user_model().objects.select_for_update().get(pk=user.pk)
    if locked_user.phone_verified_at is not None:
        raise ValidationError({"detail": "Ce numéro est déjà vérifié."})

    now = timezone.now()
    recent = OtpCode.objects.filter(user=locked_user, created_at__gte=now - timedelta(hours=24))
    if recent.count() >= 5:
        raise Throttled(detail="Limite quotidienne de codes atteinte.")

    latest = recent.order_by("-created_at").first()
    if latest and latest.created_at + timedelta(seconds=60) > now:
        raise Throttled(wait=60, detail="Attendez avant de demander un autre code.")

    provider = get_sms_provider(host, remote_addr)
    code = f"{secrets.randbelow(1_000_000):06d}"
    OtpCode.objects.filter(user=locked_user, consumed_at__isnull=True).update(consumed_at=now)
    OtpCode.objects.create(user=locked_user, code_hash=make_password(code), expires_at=now + timedelta(minutes=5))
    provider.send_sms(locked_user.phone, f"Votre code BKO Services : {code}. Il expire dans 5 minutes.")


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
    if otp.attempts >= 5:
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
