from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    service_request_id = serializers.UUIDField(read_only=True)
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = (
            "id",
            "kind",
            "title",
            "message",
            "service_request_id",
            "is_read",
            "read_at",
            "created_at",
        )
        read_only_fields = fields

    def get_is_read(self, obj):
        return obj.read_at is not None


class PushKeysSerializer(serializers.Serializer):
    p256dh = serializers.CharField(max_length=255)
    auth = serializers.CharField(max_length=255)


class PushSubscriptionInputSerializer(serializers.Serializer):
    endpoint = serializers.URLField(max_length=1000)
    keys = PushKeysSerializer()


class PushUnsubscribeSerializer(serializers.Serializer):
    endpoint = serializers.URLField(max_length=1000)


class PushSubscriptionSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    endpoint = serializers.URLField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
