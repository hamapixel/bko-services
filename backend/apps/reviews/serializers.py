from rest_framework import serializers

from .models import Review


class CreateReviewSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")


class ReviewSerializer(serializers.ModelSerializer):
    provider_id = serializers.UUIDField(read_only=True)
    request_id = serializers.UUIDField(source="service_request_id", read_only=True)

    class Meta:
        model = Review
        fields = ("id", "request_id", "provider_id", "rating", "comment", "created_at")
        read_only_fields = fields


class PublicReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ("id", "rating", "comment", "created_at")
        read_only_fields = fields
