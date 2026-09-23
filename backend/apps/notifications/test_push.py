import base64
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from pywebpush import WebPushException
from rest_framework.test import APIClient

from .models import Notification, PushSubscription
from .services import create_notification, send_push_for_notification


class GonePushError(WebPushException):
    @property
    def status_code(self):
        return 410


class WebPushTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            phone="+22370000000",
            password="Strong-password-2026!",
            phone_verified_at=timezone.now(),
        )
        self.other_user = get_user_model().objects.create_user(
            phone="+22370000001",
            password="Strong-password-2026!",
            phone_verified_at=timezone.now(),
        )
        self.endpoint = "https://push.example.com/subscriptions/device-1"
        self.payload = {
            "endpoint": self.endpoint,
            "keys": {
                "p256dh": "p256dh-key",
                "auth": "auth-key",
            },
        }

    @override_settings(
        WEB_PUSH_VAPID_PUBLIC_KEY="",
        WEB_PUSH_VAPID_PRIVATE_KEY="",
        WEB_PUSH_VAPID_SUBJECT="",
    )
    def test_public_config_reports_disabled_without_vapid_keys(self):
        response = APIClient().get("/api/v1/notifications/push/config/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"enabled": False, "publicKey": ""})

    @override_settings(
        WEB_PUSH_VAPID_PUBLIC_KEY="",
        WEB_PUSH_VAPID_PRIVATE_KEY="",
        WEB_PUSH_VAPID_SUBJECT="",
    )
    def test_notification_does_not_schedule_push_when_vapid_is_disabled(self):
        with patch("apps.notifications.services.send_push_for_notification") as mocked:
            with self.captureOnCommitCallbacks(execute=True):
                create_notification(
                    recipient_id=self.user.pk,
                    kind=Notification.Kind.REQUEST_ACCEPTED,
                    title="Prestataire attribué",
                    message="Un prestataire a accepté.",
                    service_request=None,
                )
        mocked.assert_not_called()

    def test_generate_vapid_keys_command_outputs_usable_public_key(self):
        output = StringIO()
        call_command("generate_vapid_keys", stdout=output)
        values = {}
        for line in output.getvalue().splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                values[key] = value

        public_key = values["WEB_PUSH_VAPID_PUBLIC_KEY"]
        private_key = values["WEB_PUSH_VAPID_PRIVATE_KEY"]
        padding = "=" * ((4 - len(public_key) % 4) % 4)
        public_bytes = base64.urlsafe_b64decode(public_key + padding)

        self.assertEqual(len(public_bytes), 65)
        self.assertTrue(private_key)
        self.assertEqual(
            values["WEB_PUSH_VAPID_SUBJECT"],
            "mailto:votre-email@example.com",
        )

    @override_settings(
        WEB_PUSH_VAPID_PUBLIC_KEY="public-key",
        WEB_PUSH_VAPID_PRIVATE_KEY="private-key",
        WEB_PUSH_VAPID_SUBJECT="mailto:admin@example.com",
    )
    def test_public_config_exposes_only_public_vapid_key(self):
        response = APIClient().get("/api/v1/notifications/push/config/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"enabled": True, "publicKey": "public-key"},
        )
        self.assertNotIn("private", str(response.json()).lower())

    def test_authenticated_user_can_register_and_unregister_own_subscription(self):
        api = APIClient()
        api.force_login(self.user)

        created = api.post(
            "/api/v1/notifications/push/subscriptions/",
            self.payload,
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        body = created.json()
        self.assertEqual(body["endpoint"], self.endpoint)
        self.assertNotIn("p256dh", body)
        self.assertNotIn("auth", body)

        subscription = PushSubscription.objects.get()
        self.assertEqual(subscription.user, self.user)
        self.assertEqual(subscription.p256dh, "p256dh-key")
        self.assertTrue(subscription.is_active)

        foreign = APIClient()
        foreign.force_login(self.other_user)
        self.assertEqual(
            foreign.delete(
                "/api/v1/notifications/push/subscriptions/",
                {"endpoint": self.endpoint},
                format="json",
            ).status_code,
            404,
        )
        self.assertTrue(PushSubscription.objects.filter(pk=subscription.pk).exists())

        deleted = api.delete(
            "/api/v1/notifications/push/subscriptions/",
            {"endpoint": self.endpoint},
            format="json",
        )
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(PushSubscription.objects.exists())

    def test_same_browser_endpoint_is_reassigned_to_current_account(self):
        first = APIClient()
        first.force_login(self.user)
        self.assertEqual(
            first.post(
                "/api/v1/notifications/push/subscriptions/",
                self.payload,
                format="json",
            ).status_code,
            201,
        )

        second = APIClient()
        second.force_login(self.other_user)
        changed_payload = {
            "endpoint": self.endpoint,
            "keys": {
                "p256dh": "new-p256dh-key",
                "auth": "new-auth-key",
            },
        }
        self.assertEqual(
            second.post(
                "/api/v1/notifications/push/subscriptions/",
                changed_payload,
                format="json",
            ).status_code,
            201,
        )

        self.assertEqual(PushSubscription.objects.count(), 1)
        subscription = PushSubscription.objects.get()
        self.assertEqual(subscription.user, self.other_user)
        self.assertEqual(subscription.p256dh, "new-p256dh-key")
        self.assertEqual(subscription.auth, "new-auth-key")

    def test_unknown_client_fields_are_rejected(self):
        api = APIClient()
        api.force_login(self.user)
        response = api.post(
            "/api/v1/notifications/push/subscriptions/",
            {**self.payload, "user_id": str(self.other_user.pk)},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(PushSubscription.objects.count(), 0)

    @override_settings(
        WEB_PUSH_VAPID_PUBLIC_KEY="public-key",
        WEB_PUSH_VAPID_PRIVATE_KEY="private-key",
        WEB_PUSH_VAPID_SUBJECT="mailto:admin@example.com",
    )
    def test_new_internal_notification_schedules_push_after_commit_once(self):
        with patch("apps.notifications.services.send_push_for_notification") as mocked:
            with self.captureOnCommitCallbacks(execute=True):
                first = create_notification(
                    recipient_id=self.user.pk,
                    kind=Notification.Kind.REQUEST_ACCEPTED,
                    title="Prestataire attribué",
                    message="Un prestataire a accepté.",
                    service_request=None,
                )
            with self.captureOnCommitCallbacks(execute=True):
                second = create_notification(
                    recipient_id=self.user.pk,
                    kind=Notification.Kind.REQUEST_ACCEPTED,
                    title="Prestataire attribué",
                    message="Un prestataire a accepté.",
                    service_request=None,
                )

        self.assertEqual(first.pk, second.pk)
        mocked.assert_called_once_with(first.pk)

    @override_settings(
        WEB_PUSH_VAPID_PUBLIC_KEY="public-key",
        WEB_PUSH_VAPID_PRIVATE_KEY="private-key",
        WEB_PUSH_VAPID_SUBJECT="mailto:admin@example.com",
    )
    @patch("apps.notifications.services.webpush")
    def test_successful_push_resets_failures_and_records_success(self, mocked_webpush):
        notification = Notification.objects.create(
            recipient=self.user,
            kind=Notification.Kind.REQUEST_ACCEPTED,
            title="Prestataire attribué",
            message="Un prestataire a accepté.",
        )
        subscription = PushSubscription.objects.create(
            user=self.user,
            endpoint=self.endpoint,
            p256dh="p256dh-key",
            auth="auth-key",
            failure_count=3,
        )

        delivered = send_push_for_notification(notification.pk)

        self.assertEqual(delivered, 1)
        mocked_webpush.assert_called_once()
        subscription.refresh_from_db()
        self.assertEqual(subscription.failure_count, 0)
        self.assertTrue(subscription.is_active)
        self.assertIsNotNone(subscription.last_success_at)

        call = mocked_webpush.call_args.kwargs
        self.assertEqual(call["subscription_info"]["endpoint"], self.endpoint)
        self.assertEqual(call["vapid_private_key"], "private-key")
        self.assertEqual(call["vapid_claims"], {"sub": "mailto:admin@example.com"})
        self.assertIn('"title":"Prestataire attribué"', call["data"])

    @override_settings(
        WEB_PUSH_VAPID_PUBLIC_KEY="public-key",
        WEB_PUSH_VAPID_PRIVATE_KEY="private-key",
        WEB_PUSH_VAPID_SUBJECT="mailto:admin@example.com",
    )
    @patch("apps.notifications.services.webpush", side_effect=GonePushError("gone"))
    def test_expired_push_endpoint_is_disabled(self, mocked_webpush):
        notification = Notification.objects.create(
            recipient=self.user,
            kind=Notification.Kind.REQUEST_ACCEPTED,
            title="Prestataire attribué",
            message="Un prestataire a accepté.",
        )
        subscription = PushSubscription.objects.create(
            user=self.user,
            endpoint=self.endpoint,
            p256dh="p256dh-key",
            auth="auth-key",
        )

        delivered = send_push_for_notification(notification.pk)

        self.assertEqual(delivered, 0)
        mocked_webpush.assert_called_once()
        subscription.refresh_from_db()
        self.assertFalse(subscription.is_active)
        self.assertEqual(subscription.failure_count, 1)
