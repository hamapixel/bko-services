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
