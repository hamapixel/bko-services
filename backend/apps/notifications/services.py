from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound

from .models import Notification


def create_notification(*, recipient_id, kind, title, message, service_request):
    notification, _ = Notification.objects.get_or_create(
        recipient_id=recipient_id,
        service_request=service_request,
        kind=kind,
        defaults={
            "title": title,
            "message": message,
        },
    )
    return notification


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
