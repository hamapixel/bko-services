import re
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import OtpCode
from .otp_delivery import ConsoleSmsProvider


class SessionAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)
        response = self.client.get("/api/v1/auth/csrf/")
        self.csrf_token = response.json()["csrfToken"]

    def post(self, path, data, *, csrf=True):
        headers = {"HTTP_X_CSRFTOKEN": self.csrf_token} if csrf else {}
        return self.client.post(path, data, format="json", **headers)

    def test_registration_ignores_client_supplied_role_by_rejecting_request(self):
        payload = {"phone": "+22312345678", "password": "Complex-password-2026!", "role": "SUPERADMIN"}
        self.assertEqual(self.post("/api/v1/auth/register/", payload, csrf=False).status_code, 403)
        self.assertEqual(self.post("/api/v1/auth/register/", [{"role": "SUPERADMIN"}]).status_code, 400)
        response = self.post("/api/v1/auth/register/", payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(get_user_model().objects.count(), 0)

        payload.pop("role")
        response = self.post("/api/v1/auth/register/", payload)
        self.assertEqual(response.status_code, 201)
        user = get_user_model().objects.get()
        self.assertEqual(user.role, user.Role.CLIENT)
        self.assertIsNone(user.phone_verified_at)
        self.assertNotIn("password", response.json())

    def test_session_login_profile_and_logout_require_csrf(self):
        user = get_user_model().objects.create_user(phone="+22312345678", password="Complex-password-2026!")
        path = "/api/v1/auth/login/"
        payload = {"phone": user.phone, "password": "Complex-password-2026!"}
        self.assertEqual(self.post(path, payload, csrf=False).status_code, 403)
        self.assertEqual(self.post(path, payload).status_code, 200)
        self.assertTrue(self.client.cookies["sessionid"]["httponly"])
        self.csrf_token = self.client.get("/api/v1/auth/csrf/").json()["csrfToken"]

        self.assertEqual(self.client.get("/api/v1/auth/me/").json()["role"], "CLIENT")
        response = self.client.patch(
            "/api/v1/auth/me/", {"role": "SUPERADMIN"}, format="json", HTTP_X_CSRFTOKEN=self.csrf_token
        )
        self.assertEqual(response.status_code, 400)
        user.refresh_from_db()
        self.assertEqual(user.role, user.Role.CLIENT)

        self.assertEqual(self.post("/api/v1/auth/logout/", {}, csrf=False).status_code, 403)
        self.assertEqual(self.post("/api/v1/auth/logout/", {}).status_code, 204)
        self.assertNotEqual(self.client.get("/api/v1/auth/me/").status_code, 200)


class PhoneOtpTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(phone="+22312345678", password="Complex-password-2026!")
        self.client = APIClient(enforce_csrf_checks=True, HTTP_HOST="localhost")
        self.client.force_login(self.user)
        self.token = self.client.get("/api/v1/auth/csrf/").json()["csrfToken"]

    def post(self, path, data=None, *, csrf=True):
        headers = {"HTTP_X_CSRFTOKEN": self.token} if csrf else {}
        return self.client.post(path, data or {}, format="json", **headers)

    @override_settings(DEBUG=True, SMS_PROVIDER="")
    def test_otp_is_hashed_limited_and_single_use(self):
        path = "/api/v1/auth/phone/request-code/"
        self.assertEqual(self.post(path, csrf=False).status_code, 403)
        with patch.object(ConsoleSmsProvider, "send_sms") as send_sms:
            response = self.post(path)
            self.assertEqual(response.status_code, 200)
            message = send_sms.call_args.args[1]
        code = re.search(r"\b\d{6}\b", message).group()
        otp = OtpCode.objects.get()
        self.assertNotIn(code, str(response.json()))
        self.assertNotEqual(otp.code_hash, code)
        self.assertTrue(check_password(code, otp.code_hash))
        self.assertEqual(self.post(path).status_code, 429)

        verify = "/api/v1/auth/phone/verify/"
        self.assertEqual(self.post(verify, {"code": "000000" if code != "000000" else "111111"}).status_code, 400)
        otp.refresh_from_db()
        self.assertEqual(otp.attempts, 1)
        self.assertEqual(self.post(verify, {"code": code}).status_code, 200)
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.phone_verified_at)
        self.assertEqual(self.post(verify, {"code": code}).status_code, 400)

    @override_settings(DEBUG=False, SMS_PROVIDER="")
    def test_production_refuses_otp_without_sms_provider(self):
        self.assertEqual(self.post("/api/v1/auth/phone/request-code/").status_code, 503)
        self.assertEqual(OtpCode.objects.count(), 0)

    def test_five_wrong_codes_lock_the_otp(self):
        otp = OtpCode.objects.create(
            user=self.user, code_hash=make_password("123456"), expires_at=timezone.now() + timedelta(minutes=5)
        )
        path = "/api/v1/auth/phone/verify/"
        for _ in range(5):
            self.assertEqual(self.post(path, {"code": "999999"}).status_code, 400)
        otp.refresh_from_db()
        self.assertEqual(otp.attempts, 5)
        self.assertEqual(self.post(path, {"code": "123456"}).status_code, 429)
        self.user.refresh_from_db()
        self.assertIsNone(self.user.phone_verified_at)
