from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient


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
