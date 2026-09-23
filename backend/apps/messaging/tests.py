import base64
from urllib.parse import parse_qs
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import Throttled
from rest_framework.test import APIClient

from apps.accounts.models import OtpCode
from apps.accounts.otp_service import request_verification_code

from .models import SmsDeliveryLog
from .providers import (
    ConsoleSmsProvider,
    DeliveryUnavailable,
    SmsDeliveryError,
    TwilioSmsProvider,
)


class FakeTwilioResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self.payload


class SmsTransportTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            phone="+22371000000",
            password="Strong-password-2026!",
        )

    @override_settings(
        SMS_PROVIDER="twilio",
        TWILIO_ACCOUNT_SID="AC11111111111111111111111111111111",
        TWILIO_AUTH_TOKEN="secret-token",
        TWILIO_MESSAGING_SERVICE_SID="MG22222222222222222222222222222222",
        TWILIO_FROM_NUMBER="",
        SMS_HTTP_TIMEOUT_SECONDS=5,
    )
    def test_twilio_provider_uses_official_https_message_endpoint(self):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return FakeTwilioResponse(
                b'{"sid":"SM33333333333333333333333333333333","status":"queued"}'
            )

        with patch("apps.messaging.providers.urlopen", side_effect=fake_urlopen):
            result = TwilioSmsProvider().send_sms(
                self.user.phone,
                "Code test 123456",
            )

        request = captured["request"]
        form = parse_qs(request.data.decode("utf-8"))
        expected_auth = base64.b64encode(
            b"AC11111111111111111111111111111111:secret-token"
        ).decode("ascii")

        self.assertEqual(
            request.full_url,
            "https://api.twilio.com/2010-04-01/Accounts/"
            "AC11111111111111111111111111111111/Messages.json",
        )
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Authorization"), f"Basic {expected_auth}")
        self.assertEqual(form["To"], [self.user.phone])
        self.assertEqual(form["Body"], ["Code test 123456"])
        self.assertEqual(
            form["MessagingServiceSid"],
            ["MG22222222222222222222222222222222"],
        )
        self.assertNotIn("From", form)
        self.assertEqual(captured["timeout"], 5)
        self.assertEqual(result.message_id, "SM33333333333333333333333333333333")
        self.assertEqual(result.provider_status, "queued")

    @override_settings(
        DEBUG=False,
        SMS_PROVIDER="console",
    )
    def test_console_transport_is_forbidden_outside_local_development(self):
        with self.assertRaises(DeliveryUnavailable):
            from .providers import get_sms_provider

            get_sms_provider("example.com", "203.0.113.10")

    @override_settings(
        DEBUG=False,
        SMS_PROVIDER="twilio",
        TWILIO_ACCOUNT_SID="",
        TWILIO_AUTH_TOKEN="",
        TWILIO_MESSAGING_SERVICE_SID="",
        TWILIO_FROM_NUMBER="",
    )
    def test_incomplete_twilio_configuration_creates_no_otp_or_log(self):
        api = APIClient()
        api.force_login(self.user)

        response = api.post("/api/v1/auth/phone/request-code/", {}, format="json")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(OtpCode.objects.count(), 0)
        self.assertEqual(SmsDeliveryLog.objects.count(), 0)

    @override_settings(
        DEBUG=False,
        SMS_PROVIDER="twilio",
        TWILIO_ACCOUNT_SID="AC11111111111111111111111111111111",
        TWILIO_AUTH_TOKEN="secret-token",
        TWILIO_MESSAGING_SERVICE_SID="MG22222222222222222222222222222222",
        TWILIO_FROM_NUMBER="",
    )
    def test_delivery_failure_invalidates_otp_and_is_audited_without_message_body(self):
        api = APIClient()
        api.force_login(self.user)

        with patch.object(
            TwilioSmsProvider,
            "send_sms",
            side_effect=SmsDeliveryError("twilio_network"),
        ):
            response = api.post(
                "/api/v1/auth/phone/request-code/",
                {},
                format="json",
                REMOTE_ADDR="198.51.100.10",
                HTTP_HOST="example.com",
            )

        self.assertEqual(response.status_code, 503)
        otp = OtpCode.objects.get()
        self.assertIsNotNone(otp.consumed_at)

        log = SmsDeliveryLog.objects.get()
        self.assertEqual(log.status, SmsDeliveryLog.Status.FAILED)
        self.assertEqual(log.provider, SmsDeliveryLog.Provider.TWILIO)
        self.assertEqual(log.error_code, "twilio_network")
        self.assertFalse(hasattr(log, "message"))
        self.assertFalse(hasattr(log, "body"))

    @override_settings(
        DEBUG=True,
        SMS_PROVIDER="",
        SMS_OTP_IP_LIMIT_PER_HOUR=2,
    )
    def test_shared_database_ip_limit_applies_across_accounts(self):
        users = [
            self.user,
            get_user_model().objects.create_user(
                phone="+22371000001",
                password="Strong-password-2026!",
            ),
            get_user_model().objects.create_user(
                phone="+22371000002",
                password="Strong-password-2026!",
            ),
        ]

        with patch.object(ConsoleSmsProvider, "send_sms"):
            request_verification_code(users[0], "localhost", "127.0.0.1")
            request_verification_code(users[1], "localhost", "127.0.0.1")
            with self.assertRaises(Throttled):
                request_verification_code(users[2], "localhost", "127.0.0.1")

        self.assertEqual(SmsDeliveryLog.objects.count(), 2)
        hashes = set(SmsDeliveryLog.objects.values_list("request_ip_hash", flat=True))
        self.assertEqual(len(hashes), 1)
        self.assertNotIn("127.0.0.1", hashes)

    @override_settings(
        DEBUG=True,
        SMS_PROVIDER="",
    )
    def test_successful_local_otp_creates_accepted_log_without_plaintext_code(self):
        with patch.object(ConsoleSmsProvider, "send_sms") as send_sms:
            request_verification_code(self.user, "localhost", "127.0.0.1")

        message = send_sms.call_args.args[1]
        otp = OtpCode.objects.get()
        log = SmsDeliveryLog.objects.get()

        self.assertEqual(log.status, SmsDeliveryLog.Status.ACCEPTED)
        self.assertEqual(log.provider, SmsDeliveryLog.Provider.CONSOLE)
        self.assertEqual(log.recipient, self.user.phone)
        self.assertTrue(log.request_ip_hash)
        self.assertNotIn(message, str(log.__dict__))
        self.assertNotIn("Votre code BKO Services", str(log.__dict__))
        self.assertIsNone(self.user.phone_verified_at)
