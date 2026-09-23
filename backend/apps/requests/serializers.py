from rest_framework import serializers

from apps.catalog.models import Trade
from apps.locations.models import Neighborhood

from .models import RequestStatusHistory, ServiceRequest


class CreateRequestSerializer(serializers.Serializer):
    trade = serializers.PrimaryKeyRelatedField(queryset=Trade.objects.filter(is_active=True, category__is_active=True))
    neighborhood = serializers.PrimaryKeyRelatedField(
        queryset=Neighborhood.objects.filter(is_active=True, commune__is_active=True, commune__city__is_active=True)
    )
    title = serializers.CharField(max_length=150)
    description = serializers.CharField(max_length=2000)
    address_detail = serializers.CharField(max_length=250)
    priority = serializers.ChoiceField(choices=ServiceRequest.Priority.choices, default=ServiceRequest.Priority.NORMAL)


class StatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestStatusHistory
        fields = ("previous_status", "new_status", "created_at")
        read_only_fields = fields


class OwnRequestSerializer(serializers.ModelSerializer):
    status_history = StatusHistorySerializer(many=True, read_only=True)
    assigned_provider_id = serializers.UUIDField(read_only=True)
    assigned_provider_display_name = serializers.SerializerMethodField()
    assigned_provider_phone = serializers.SerializerMethodField()

    class Meta:
        model = ServiceRequest
        fields = (
            "id", "trade", "neighborhood", "title", "description", "address_detail",
            "priority", "status", "assigned_provider_id", "assigned_provider_display_name",
            "assigned_provider_phone", "created_at", "updated_at", "status_history",
        )
        read_only_fields = fields

    def get_assigned_provider_display_name(self, obj):
        return obj.assigned_provider.display_name if obj.assigned_provider_id else None

    def get_assigned_provider_phone(self, obj):
        return obj.assigned_provider.user.phone if obj.assigned_provider_id else None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not instance.assigned_provider_id:
            data.pop("assigned_provider_id", None)
            data.pop("assigned_provider_display_name", None)
            data.pop("assigned_provider_phone", None)
        return data


class ProviderInterventionSerializer(serializers.ModelSerializer):
    status_history = StatusHistorySerializer(many=True, read_only=True)
    client_phone = serializers.CharField(source="client.phone", read_only=True)

    class Meta:
        model = ServiceRequest
        fields = (
            "id", "trade", "neighborhood", "title", "description", "address_detail",
            "priority", "status", "client_phone", "created_at", "updated_at", "status_history",
        )
        read_only_fields = fields
