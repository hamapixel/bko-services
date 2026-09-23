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

    class Meta:
        model = ServiceRequest
        fields = (
            "id", "trade", "neighborhood", "title", "description", "address_detail",
            "priority", "status", "created_at", "updated_at", "status_history",
        )
        read_only_fields = fields
