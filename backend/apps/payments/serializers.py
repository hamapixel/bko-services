from rest_framework import serializers

from .models import PaymentTransaction


class PaymentCreateSerializer(serializers.Serializer):
    plan_id = serializers.UUIDField()
    idempotency_key = serializers.RegexField(
        regex=r"^[A-Za-z0-9._:-]{8,64}$",
        max_length=64,
    )


class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = (
            "id",
            "merchant_reference",
            "purpose",
            "payment_provider",
            "amount_xof",
            "currency",
            "plan_code_snapshot",
            "plan_name_snapshot",
            "duration_days_snapshot",
            "status",
            "confirmed_at",
            "fulfilled_at",
            "fulfillment_error_code",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AdminPaymentTransactionSerializer(PaymentTransactionSerializer):
    provider_id = serializers.UUIDField(read_only=True)
    provider_display_name = serializers.CharField(
        source="provider.display_name",
        read_only=True,
    )
    provider_transaction_id = serializers.CharField(read_only=True)

    class Meta(PaymentTransactionSerializer.Meta):
        fields = PaymentTransactionSerializer.Meta.fields + (
            "provider_id",
            "provider_display_name",
            "provider_transaction_id",
        )


class PaymentWebhookSerializer(serializers.Serializer):
    merchant_reference = serializers.CharField(max_length=64)
    provider_transaction_id = serializers.CharField(max_length=128)
    status = serializers.ChoiceField(
        choices=("SUCCESS", "FAILED", "CANCELLED"),
    )
    amount_xof = serializers.IntegerField(min_value=0)
    currency = serializers.CharField(min_length=3, max_length=3)
