from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import (
    NotificationSerializer,
    PushSubscriptionInputSerializer,
    PushSubscriptionSerializer,
    PushUnsubscribeSerializer,
)
from .services import (
    mark_all_notifications_read,
    mark_notification_read,
    register_push_subscription,
    unregister_push_subscription,
    web_push_configured,
)


class NotificationListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        queryset = Notification.objects.filter(recipient=self.request.user)
        unread = self.request.query_params.get("unread")
        if unread == "true":
            queryset = queryset.filter(read_at__isnull=True)
        return queryset


class UnreadNotificationCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(
            recipient=request.user,
            read_at__isnull=True,
        ).count()
        return Response({"unread_count": count})


class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = mark_notification_read(pk, request.user)
        return Response(NotificationSerializer(notification).data)


class NotificationReadAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated = mark_all_notifications_read(request.user)
        return Response(
            {"marked_read": updated},
            status=status.HTTP_200_OK,
        )


class PushConfigView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        enabled = web_push_configured()
        from django.conf import settings

        return Response(
            {
                "enabled": enabled,
                "publicKey": settings.WEB_PUSH_VAPID_PUBLIC_KEY if enabled else "",
            }
        )


class PushSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not isinstance(request.data, dict) or set(request.data) - set(PushSubscriptionInputSerializer().fields):
            raise ValidationError({"detail": "Champ non autorisé."})

        serializer = PushSubscriptionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscription = register_push_subscription(
            request.user,
            **serializer.validated_data,
        )
        return Response(
            PushSubscriptionSerializer(subscription).data,
            status=status.HTTP_201_CREATED,
        )

    def delete(self, request):
        if not isinstance(request.data, dict) or set(request.data) - set(PushUnsubscribeSerializer().fields):
            raise ValidationError({"detail": "Champ non autorisé."})

        serializer = PushUnsubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        unregister_push_subscription(
            request.user,
            serializer.validated_data["endpoint"],
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
