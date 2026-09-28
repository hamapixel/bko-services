from rest_framework import serializers

from apps.catalog.models import Trade
from apps.locations.models import Neighborhood, Region, City

from .models import RequestStatusHistory, ServiceRequest


class CreateRequestSerializer(serializers.Serializer):
    trade = serializers.PrimaryKeyRelatedField(queryset=Trade.objects.filter(is_active=True, category__is_active=True))
    neighborhood = serializers.PrimaryKeyRelatedField(
        required=False, queryset=Neighborhood.objects.filter(is_active=True, commune__is_active=True, commune__city__is_active=True, commune__city__region__is_active=True)
    )
    requested_region = serializers.PrimaryKeyRelatedField(required=False, queryset=Region.objects.filter(is_active=True))
    requested_city = serializers.CharField(required=False, max_length=120, trim_whitespace=True)
    requested_commune = serializers.CharField(required=False, max_length=120, trim_whitespace=True)
    requested_neighborhood = serializers.CharField(required=False, max_length=120, trim_whitespace=True)
    title = serializers.CharField(max_length=150)
    description = serializers.CharField(max_length=2000)
    address_detail = serializers.CharField(max_length=250)
    priority = serializers.ChoiceField(choices=ServiceRequest.Priority.choices, default=ServiceRequest.Priority.NORMAL)

    def validate(self, attrs):
        manual = any(key.startswith("requested_") for key in attrs)
        if manual:
            if "neighborhood" in attrs or not all(attrs.get(key) for key in (
                "requested_region", "requested_city", "requested_commune", "requested_neighborhood",
            )):
                raise serializers.ValidationError("Indiquez la région, la ville, la commune et le quartier, sans choisir un quartier du catalogue.")
            region = attrs["requested_region"]
            if City.objects.filter(
                region=region, is_active=True, communes__is_active=True,
                communes__neighborhoods__is_active=True,
            ).exists():
                raise serializers.ValidationError({"requested_region": "Cette région possède déjà des quartiers ouverts. Choisissez un quartier dans la liste."})
        elif "neighborhood" not in attrs:
            raise serializers.ValidationError({"neighborhood": "Choisissez un quartier ou indiquez une zone non répertoriée."})
        return attrs


class StatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestStatusHistory
        fields = ("previous_status", "new_status", "created_at")
        read_only_fields = fields


class OwnRequestSerializer(serializers.ModelSerializer):
    status_history = StatusHistorySerializer(many=True, read_only=True)
    trade_name = serializers.CharField(source="trade.name", read_only=True)
    neighborhood_name = serializers.SerializerMethodField()
    commune_name = serializers.SerializerMethodField()
    region_name = serializers.SerializerMethodField()
    has_review = serializers.SerializerMethodField()
    assigned_provider_id = serializers.UUIDField(read_only=True)
    assigned_provider_display_name = serializers.SerializerMethodField()
    assigned_provider_phone = serializers.SerializerMethodField()

    class Meta:
        model = ServiceRequest
        fields = (
            "id", "trade", "trade_name", "neighborhood", "neighborhood_name", "commune_name", "region_name", "requested_city",
            "title", "description", "address_detail", "priority", "status", "has_review",
            "assigned_provider_id", "assigned_provider_display_name",
            "assigned_provider_phone", "created_at", "updated_at", "status_history",
        )
        read_only_fields = fields

    def get_neighborhood_name(self, obj):
        return obj.neighborhood.name if obj.neighborhood_id else obj.requested_neighborhood

    def get_commune_name(self, obj):
        return obj.neighborhood.commune.name if obj.neighborhood_id else obj.requested_commune

    def get_region_name(self, obj):
        return (obj.neighborhood.commune.city.region.name if obj.neighborhood_id
                else obj.requested_region.name)

    def get_has_review(self, obj):
        return hasattr(obj, "review")

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
    trade_name = serializers.CharField(source="trade.name", read_only=True)
    neighborhood_name = serializers.CharField(source="neighborhood.name", read_only=True)
    commune_name = serializers.CharField(source="neighborhood.commune.name", read_only=True)
    client_phone = serializers.CharField(source="client.phone", read_only=True)

    class Meta:
        model = ServiceRequest
        fields = (
            "id", "trade", "trade_name", "neighborhood", "neighborhood_name", "commune_name",
            "title", "description", "address_detail", "priority", "status",
            "client_phone", "created_at", "updated_at", "status_history",
        )
        read_only_fields = fields
