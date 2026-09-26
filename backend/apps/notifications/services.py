import json
import logging
from urllib.parse import urlsplit

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from pywebpush import WebPushException, webpush
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from .models import Notification, PushSubscription


logger = logging.getLogger(__name__)


def is_allowed_push_endpoint(endpoint):
    """Only browser push services may receive server-side notification requests."""
    try:
        parsed = urlsplit(endpoint)
        host = parsed.hostname or ""
        port = parsed.port
    except ValueError:
        return False
    if (parsed.scheme != "https" or port not in (None, 443)
            or parsed.username or parsed.password or parsed.fragment or not parsed.path):
        return False
    return (
        host in {"fcm.googleapis.com", "android.googleapis.com", "updates.push.services.mozilla.com"}
        or host.endswith(".push.apple.com")
        or host.endswith(".notify.windows.com")
    )


def web_push_configured():
    subject = settings.WEB_PUSH_VAPID_SUBJECT
    valid_subject = subject.startswith("mailto:") or subject.startswith("https://")
    return bool(
        settings.WEB_PUSH_VAPID_PUBLIC_KEY
        and settings.WEB_PUSH_VAPID_PRIVATE_KEY
        and valid_subject
    )


def create_notification(*, recipient_id, kind, title, message, service_request):
    notification, created = Notification.objects.get_or_create(
        recipient_id=recipient_id,
        service_request=service_request,
        kind=kind,
        defaults={
            "title": title,
            "message": message,
        },
    )
    if created and web_push_configured():
        transaction.on_commit(
            lambda notification_id=notification.pk: send_push_for_notification(notification_id),
            robust=True,
        )
    return notification


def _push_payload(notification):
    return json.dumps(
        {
            "notificationId": str(notification.pk),
            "requestId": str(notification.service_request_id) if notification.service_request_id else None,
            "kind": notification.kind,
            "title": notification.title,
            "body": notification.message,
            "url": "/",
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def send_push_for_notification(notification_id):
    if not web_push_configured():
        return 0

    try:
        notification = Notification.objects.get(pk=notification_id)
    except Notification.DoesNotExist:
        return 0

    payload = _push_payload(notification)
    delivered = 0

    for subscription in PushSubscription.objects.filter(
        user_id=notification.recipient_id,
        is_active=True,
    ):
        if not is_allowed_push_endpoint(subscription.endpoint):
            subscription.is_active = False
            subscription.save(update_fields=["is_active", "updated_at"])
            continue
        subscription_info = {
            "endpoint": subscription.endpoint,
            "keys": {
                "p256dh": subscription.p256dh,
                "auth": subscription.auth,
            },
        }
        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=settings.WEB_PUSH_VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.WEB_PUSH_VAPID_SUBJECT},
                ttl=300,
                timeout=5,
            )
        except WebPushException as exc:
            subscription.failure_count += 1
            if exc.status_code in (404, 410):
                subscription.is_active = False
            subscription.save(update_fields=["failure_count", "is_active", "updated_at"])
        except Exception:
            logger.exception("Échec inattendu lors d'un envoi Web Push.")
            subscription.failure_count += 1
            subscription.save(update_fields=["failure_count", "updated_at"])
        else:
            subscription.failure_count = 0
            subscription.last_success_at = timezone.now()
            subscription.save(
                update_fields=["failure_count", "last_success_at", "updated_at"]
            )
            delivered += 1

    return delivered


@transaction.atomic
def register_push_subscription(user, *, endpoint, keys):
    if not user.is_authenticated or not user.is_active:
        raise PermissionDenied("Un compte actif est nécessaire.")
    if not is_allowed_push_endpoint(endpoint):
        raise ValidationError({"endpoint": "Service de notifications non autorisé."})

    subscription = (
        PushSubscription.objects.select_for_update()
        .filter(endpoint=endpoint)
        .first()
    )
    if subscription is None:
        return PushSubscription.objects.create(
            user=user,
            endpoint=endpoint,
            p256dh=keys["p256dh"],
            auth=keys["auth"],
        )

    # A browser can reuse one endpoint after another user logs in. Transfer it
    # so notifications for the previous account no longer reach that browser.
    user_changed = subscription.user_id != user.pk
    subscription.user = user
    subscription.p256dh = keys["p256dh"]
    subscription.auth = keys["auth"]
    subscription.is_active = True
    subscription.failure_count = 0
    if user_changed:
        subscription.last_success_at = None
    subscription.save(
        update_fields=[
            "user",
            "p256dh",
            "auth",
            "is_active",
            "failure_count",
            "last_success_at",
            "updated_at",
        ]
    )
    return subscription


@transaction.atomic
def unregister_push_subscription(user, endpoint):
    try:
        subscription = PushSubscription.objects.select_for_update().get(
            user=user,
            endpoint=endpoint,
        )
    except PushSubscription.DoesNotExist as exc:
        raise NotFound("Abonnement push introuvable.") from exc

    subscription.delete()


@transaction.atomic
def mark_notification_read(notification_id, user):
    try:
        notification = Notification.objects.select_for_update().get(
            pk=notification_id,
            recipient=user,
        )
    except Notification.DoesNotExist as exc:
        raise NotFound("Notification introuvable.") from exc

    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at"])
    return notification


@transaction.atomic
def mark_all_notifications_read(user):
    now = timezone.now()
    return Notification.objects.filter(
        recipient=user,
        read_at__isnull=True,
    ).update(read_at=now)
