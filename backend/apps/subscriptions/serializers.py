from rest_framework import serializers

from .models import ProviderSubscription, SubscriptionHistory, SubscriptionPlan
from .services import effective_subscription_status


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = (
            "id",
            "code",
            "name",
            "description",
            "price_xof",
            "duration_days",
            "can_receive_requests",
            "can_receive_urgent_requests",
            "is_active",
            "display_order",
        )
        read_only_fields = ("id",)


class PublicSubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = (
            "id",
            "code",
            "name",
            "description",
            "price_xof",
            "duration_days",
            "can_receive_requests",
            "can_receive_urgent_requests",
        )
        read_only_fields = fields


class SubscriptionHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionHistory
        fields = (
            "action",
            "plan_code",
            "plan_name",
            "starts_at",
            "ends_at",
            "note",
            "created_at",
        )
        read_only_fields = fields


class ProviderSubscriptionSerializer(serializers.ModelSerializer):
    plan = PublicSubscriptionPlanSerializer(read_only=True)
    status = serializers.SerializerMethodField()
    history = SubscriptionHistorySerializer(many=True, read_only=True)

    class Meta:
        model = ProviderSubscription
        fields = (
            "id",
            "plan",
            "status",
            "starts_at",
            "ends_at",
            "cancelled_at",
            "history",
        )
        read_only_fields = fields

    def get_status(self, obj):
        return effective_subscription_status(obj)


class AdminProviderSubscriptionSerializer(ProviderSubscriptionSerializer):
    provider_id = serializers.UUIDField(read_only=True)
    provider_display_name = serializers.CharField(
        source="provider.display_name",
        read_only=True,
    )
    stored_status = serializers.CharField(source="status", read_only=True)

    class Meta(ProviderSubscriptionSerializer.Meta):
        fields = ProviderSubscriptionSerializer.Meta.fields + (
            "provider_id",
            "provider_display_name",
            "stored_status",
        )


class ActivateSubscriptionSerializer(serializers.Serializer):
    plan_id = serializers.UUIDField()
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)


class RenewSubscriptionSerializer(serializers.Serializer):
    plan_id = serializers.UUIDField(required=False)
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)


class CancelSubscriptionSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=500, allow_blank=False)


def validate_plan_attributes(attrs):
    receive = attrs.get("can_receive_requests")
    urgent = attrs.get("can_receive_urgent_requests")
    if urgent is True and receive is False:
        raise serializers.ValidationError(
            {
                "can_receive_urgent_requests": (
                    "Un plan autorisant les urgences doit aussi autoriser les demandes."
                )
            }
        )
    return attrs
