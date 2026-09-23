"""Development SMS transport. A real provider will replace this at the SMS stage."""

from typing import Protocol

from django.conf import settings


class DeliveryUnavailable(Exception):
    pass


class SmsProvider(Protocol):
    def send_sms(self, phone: str, message: str) -> None: ...


class ConsoleSmsProvider:
    def send_sms(self, phone: str, message: str) -> None:
        # Only used on the local development server; never print OTPs in production.
        print(f"[BKO LOCAL OTP] {message}")


def get_sms_provider(host: str, remote_addr: str) -> SmsProvider:
    if settings.DEBUG and host.split(":")[0] in {"localhost", "127.0.0.1"} and remote_addr in {"127.0.0.1", "::1"}:
        return ConsoleSmsProvider()
    raise DeliveryUnavailable("Aucun fournisseur SMS n'est encore configuré pour cet environnement.")
