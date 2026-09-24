from rest_framework import serializers

from apps.catalog.models import Trade
from apps.locations.models import Neighborhood

from .models import ProviderProfile


class ApplicationSerializer(serializers.ModelSerializer):
    trade_ids = serializers.PrimaryKeyRelatedField(
        source="trades", many=True, allow_empty=False, write_only=True,
        queryset=Trade.objects.filter(is_active=True, category__is_active=True),
    )
    area_ids = serializers.PrimaryKeyRelatedField(
        source="service_areas", many=True, allow_empty=False, write_only=True,
        queryset=Neighborhood.objects.filter(
            is_active=True, commune__is_active=True, commune__city__is_active=True
        ),
    )

    class Meta:
        model = ProviderProfile
        fields = ("legal_name", "display_name", "description", "trade_ids", "area_ids")

    def validate_trade_ids(self, values):
        if len(values) > 10 or len({trade.pk for trade in values}) != len(values):
            raise serializers.ValidationError("Choisissez au plus 10 métiers distincts.")
        return values

    def validate_area_ids(self, values):
        if len(values) > 30 or len({area.pk for area in values}) != len(values):
            raise serializers.ValidationError("Choisissez au plus 30 quartiers distincts.")
        return values


class OwnProviderSerializer(serializers.ModelSerializer):
    trades = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    service_areas = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    trade_details = serializers.SerializerMethodField()
    service_area_details = serializers.SerializerMethodField()

    class Meta:
        model = ProviderProfile
        fields = (
            "id", "legal_name", "display_name", "description", "trades", "service_areas",
            "trade_details", "service_area_details", "status", "is_available", "verified_at",
        )
        read_only_fields = fields

    def get_trade_details(self, obj):
        return [
            {"id": str(trade.pk), "name": trade.name}
            for trade in obj.trades.all().order_by("name", "id")
        ]

    def get_service_area_details(self, obj):
        return [
            {
                "id": str(area.pk),
                "name": area.name,
                "commune_name": area.commune.name,
            }
            for area in obj.service_areas.select_related("commune").all().order_by(
                "commune__name", "name", "id"
            )
        ]


class PublicProviderSerializer(serializers.ModelSerializer):
    trade_ids = serializers.SerializerMethodField()
    area_ids = serializers.SerializerMethodField()

    class Meta:
        model = ProviderProfile
        fields = ("id", "display_name", "description", "trade_ids", "area_ids")
        read_only_fields = fields

    def get_trade_ids(self, obj):
        return [str(pk) for pk in obj.trades.filter(is_active=True, category__is_active=True).values_list("pk", flat=True)]

    def get_area_ids(self, obj):
        return [
            str(pk) for pk in obj.service_areas.filter(
                is_active=True, commune__is_active=True, commune__city__is_active=True
            ).values_list("pk", flat=True)
        ]


class AvailabilitySerializer(serializers.Serializer):
    is_available = serializers.BooleanField()
