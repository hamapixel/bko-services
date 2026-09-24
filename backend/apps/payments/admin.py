from django.contrib import admin

from .models import PaymentTransaction, PaymentWebhookEvent


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "merchant_reference",
        "provider",
        "plan_name_snapshot",
        "amount_xof",
        "status",
        "fulfilled_at",
        "created_at",
    )
    list_filter = ("status", "purpose", "payment_provider")
    search_fields = (
        "merchant_reference",
        "provider_transaction_id",
        "provider__display_name",
        "provider__user__phone",
    )
    readonly_fields = (
        "id",
        "provider",
        "plan",
        "subscription",
        "purpose",
        "payment_provider",
        "merchant_reference",
        "provider_transaction_id",
        "idempotency_key",
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

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PaymentWebhookEvent)
class PaymentWebhookEventAdmin(admin.ModelAdmin):
    list_display = (
        "transaction",
        "reported_status",
        "provider_transaction_id",
        "accepted",
        "error_code",
        "received_at",
    )
    list_filter = ("accepted", "reported_status", "error_code")
    search_fields = (
        "transaction__merchant_reference",
        "provider_transaction_id",
        "event_fingerprint",
    )
    readonly_fields = (
        "id",
        "transaction",
        "event_fingerprint",
        "reported_status",
        "provider_transaction_id",
        "amount_xof",
        "currency",
        "accepted",
        "error_code",
        "received_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
