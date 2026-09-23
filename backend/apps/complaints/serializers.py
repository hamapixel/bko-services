from rest_framework import serializers

from .models import Complaint, ComplaintStatusHistory


class ComplaintCreateSerializer(serializers.Serializer):
    service_request_id = serializers.UUIDField()
    category = serializers.ChoiceField(choices=Complaint.Category.choices)
    description = serializers.CharField(max_length=2000)


class ComplaintTransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            Complaint.Status.UNDER_REVIEW,
            Complaint.Status.RESOLVED,
            Complaint.Status.REJECTED,
        ]
    )
    note = serializers.CharField(max_length=1000, required=False, allow_blank=True)


class ComplaintStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintStatusHistory
        fields = ("previous_status", "new_status", "note", "created_at")
        read_only_fields = fields


class ComplaintSerializer(serializers.ModelSerializer):
    service_request_id = serializers.UUIDField(read_only=True)
    status_history = ComplaintStatusHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Complaint
        fields = (
            "id",
            "service_request_id",
            "category",
            "description",
            "status",
            "resolution_note",
            "created_at",
            "updated_at",
            "resolved_at",
            "status_history",
        )
        read_only_fields = fields


class AdminComplaintSerializer(ComplaintSerializer):
    reporter_id = serializers.UUIDField(read_only=True)
    reporter_role = serializers.CharField(source="reporter.role", read_only=True)

    class Meta(ComplaintSerializer.Meta):
        fields = ComplaintSerializer.Meta.fields + (
            "reporter_id",
            "reporter_role",
            "previous_request_status",
        )
