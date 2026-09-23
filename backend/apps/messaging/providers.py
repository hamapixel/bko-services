import base64
import json
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings


class DeliveryUnavailable(Exception):
    pass


class SmsDeliveryError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class SmsSendResult:
    message_id: str = ""
    provider_status: str = ""


class SmsProvider(Protocol):
    provider_name: str

    def send_sms(self, phone: str, message: str) -> SmsSendResult: ...


class ConsoleSmsProvider:
    provider_name = "CONSOLE"

    def send_sms(self, phone: str, message: str) -> SmsSendResult:
        # Strictement réservé au développement local.
        print(f"[BKO LOCAL OTP] {message}")
        return SmsSendResult(provider_status="local")


class TwilioSmsProvider:
    provider_name = "TWILIO"

    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.messaging_service_sid = settings.TWILIO_MESSAGING_SERVICE_SID
        self.from_number = settings.TWILIO_FROM_NUMBER

        if not self.account_sid or not self.auth_token:
            raise DeliveryUnavailable("Identifiants Twilio incomplets.")
        if not self.messaging_service_sid and not self.from_number:
            raise DeliveryUnavailable("Aucun expéditeur Twilio n'est configuré.")

    def send_sms(self, phone: str, message: str) -> SmsSendResult:
        url = (
            "https://api.twilio.com/2010-04-01/Accounts/"
            f"{self.account_sid}/Messages.json"
        )
        payload = {
            "To": phone,
            "Body": message,
        }
        if self.messaging_service_sid:
            payload["MessagingServiceSid"] = self.messaging_service_sid
        else:
            payload["From"] = self.from_number

        credentials = base64.b64encode(
            f"{self.account_sid}:{self.auth_token}".encode("utf-8")
        ).decode("ascii")
        request = Request(
            url,
            data=urlencode(payload).encode("utf-8"),
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "BKO-Services/1.0",
            },
            method="POST",
        )

        try:
            with urlopen(
                request,
                timeout=settings.SMS_HTTP_TIMEOUT_SECONDS,
            ) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            provider_code = ""
            try:
                provider_code = str(json.loads(exc.read().decode("utf-8")).get("code", ""))
            except (ValueError, AttributeError, UnicodeDecodeError):
                pass
            suffix = provider_code or str(exc.code)
            raise SmsDeliveryError(f"twilio_http_{suffix}") from exc
        except (URLError, TimeoutError) as exc:
            raise SmsDeliveryError("twilio_network") from exc
        except (ValueError, UnicodeDecodeError) as exc:
            raise SmsDeliveryError("twilio_invalid_response") from exc

        if not isinstance(body, dict):
            raise SmsDeliveryError("twilio_invalid_response")

        message_id = str(body.get("sid", ""))
        provider_status = str(body.get("status", ""))
        if not message_id:
            raise SmsDeliveryError("twilio_missing_message_id")
        return SmsSendResult(
            message_id=message_id,
            provider_status=provider_status,
        )


def get_sms_provider(host: str, remote_addr: str) -> SmsProvider:
    provider = settings.SMS_PROVIDER.strip().lower()

    if provider in {"", "console"}:
        local_host = host.split(":")[0] in {"localhost", "127.0.0.1"}
        loopback = remote_addr in {"127.0.0.1", "::1"}
        if settings.DEBUG and local_host and loopback:
            return ConsoleSmsProvider()
        if provider == "console":
            raise DeliveryUnavailable(
                "Le transport console est interdit hors développement local."
            )

    if provider == "twilio":
        return TwilioSmsProvider()

    raise DeliveryUnavailable("Aucun fournisseur SMS n'est configuré.")
