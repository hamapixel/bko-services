import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import Throttled, ValidationError

from apps.messaging.models import SmsDeliveryLog
from apps.messaging.providers import DeliveryUnavailable, SmsDeliveryError, get_sms_provider
from apps.messaging.services import (
    create_sms_delivery_log,
    enforce_shared_otp_ip_limit,
    mark_sms_accepted,
    mark_sms_failed,
)

from .models import PasswordResetCode


GENERIC_REQUEST_DETAIL = (
    "Si ce numéro correspond à un compte client actif, un code de "
    "réinitialisation a été envoyé."
)


def request_password_reset(phone: str, host: str, remote_addr: str) -> None:
    # Resolve the transport before the account lookup so infrastructure errors
    # do not reveal whether the submitted phone number exists.
    provider = get_sms_provider(host, remote_addr)
    request_ip_hash = enforce_shared_otp_ip_limit(
        remote_addr,
        purpose=SmsDeliveryLog.Purpose.PASSWORD_RESET,
    )
    User = get_user_model()
    user = User.objects.filter(
        phone=phone,
        role=User.Role.CLIENT,
        is_active=True,
    ).first()

    if user is None:
        return

    now = timezone.now()
    with transaction.atomic():
        locked_user = User.objects.select_for_update().get(pk=user.pk)
        recent = PasswordResetCode.objects.filter(
            user=locked_user,
            created_at__gte=now - timedelta(hours=24),
        )
        # Keep the public response identical instead of disclosing rate state.
        if recent.count() >= settings.OTP_PHONE_DAILY_LIMIT:
            return

        latest = recent.order_by("-created_at").first()
        if (
            latest
            and latest.created_at
            + timedelta(seconds=settings.OTP_MIN_REQUEST_INTERVAL_SECONDS)
            > now
        ):
            return

        code = f"{secrets.randbelow(1_000_000):06d}"
        PasswordResetCode.objects.filter(
            user=locked_user,
            consumed_at__isnull=True,
        ).update(consumed_at=now)
        reset_code = PasswordResetCode.objects.create(
            user=locked_user,
            code_hash=make_password(code),
            expires_at=now + timedelta(seconds=settings.OTP_CODE_TTL_SECONDS),
        )
        delivery_log = create_sms_delivery_log(
            user=locked_user,
            recipient=locked_user.phone,
            provider=provider.provider_name,
            request_ip_hash=request_ip_hash,
            purpose=SmsDeliveryLog.Purpose.PASSWORD_RESET,
        )

    try:
        result = provider.send_sms(
            locked_user.phone,
            (
                f"Code BKO Services pour réinitialiser votre mot de passe : {code}. "
                "Il expire dans 5 minutes."
            ),
        )
    except SmsDeliveryError as exc:
        failure_time = timezone.now()
        with transaction.atomic():
            PasswordResetCode.objects.filter(
                pk=reset_code.pk,
                consumed_at__isnull=True,
            ).update(consumed_at=failure_time)
            mark_sms_failed(delivery_log.pk, exc.code)
        raise DeliveryUnavailable(
            "Le fournisseur SMS n'a pas accepté le message."
        ) from exc

    mark_sms_accepted(delivery_log.pk, result)


@transaction.atomic
def confirm_password_reset(
    *,
    phone: str,
    code: str,
    new_password: str,
) -> bool:
    User = get_user_model()
    user = (
        User.objects.select_for_update()
        .filter(
            phone=phone,
            role=User.Role.CLIENT,
            is_active=True,
        )
        .first()
    )
    if user is None:
        # Run a password hash check to reduce the timing difference with a
        # real account without creating or exposing any account data.
        check_password(code, make_password("000000"))
        return False

    reset_code = (
        PasswordResetCode.objects.select_for_update()
        .filter(user=user, consumed_at__isnull=True)
        .order_by("-created_at")
        .first()
    )
    now = timezone.now()
    if reset_code is None or reset_code.expires_at <= now:
        return False
    if reset_code.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise Throttled(detail="Trop de tentatives pour ce code.")

    if not check_password(code, reset_code.code_hash):
        reset_code.attempts += 1
        reset_code.save(update_fields=["attempts"])
        return False

    try:
        validate_password(new_password, user)
    except DjangoValidationError as exc:
        raise ValidationError({"new_password": exc.messages}) from exc

    reset_code.attempts += 1
    reset_code.consumed_at = now
    reset_code.save(update_fields=["attempts", "consumed_at"])

    # Consume any older reset code and rotate the password. Existing Django
    # sessions become invalid because the session auth hash changes.
    PasswordResetCode.objects.filter(
        user=user,
        consumed_at__isnull=True,
    ).update(consumed_at=now)
    user.set_password(new_password)
    user.save(update_fields=["password"])
    return True
