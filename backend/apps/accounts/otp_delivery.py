"""Compatibility imports for the SMS transport used by account OTP."""

from apps.messaging.providers import (
    ConsoleSmsProvider,
    DeliveryUnavailable,
    SmsDeliveryError,
    SmsProvider,
    SmsSendResult,
    TwilioSmsProvider,
    get_sms_provider,
)

__all__ = [
    "ConsoleSmsProvider",
    "DeliveryUnavailable",
    "SmsDeliveryError",
    "SmsProvider",
    "SmsSendResult",
    "TwilioSmsProvider",
    "get_sms_provider",
]
