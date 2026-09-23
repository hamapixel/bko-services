from django.urls import path

from .views import (
    NotificationListView,
    NotificationReadAllView,
    NotificationReadView,
    PushConfigView,
    PushSubscriptionView,
    UnreadNotificationCountView,
)

urlpatterns = [
    path("", NotificationListView.as_view(), name="notifications"),
    path("unread-count/", UnreadNotificationCountView.as_view(), name="notification-unread-count"),
    path("read-all/", NotificationReadAllView.as_view(), name="notification-read-all"),
    path("<uuid:pk>/read/", NotificationReadView.as_view(), name="notification-read"),
    path("push/config/", PushConfigView.as_view(), name="push-config"),
    path("push/subscriptions/", PushSubscriptionView.as_view(), name="push-subscriptions"),
]
