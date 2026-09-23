from django.contrib import admin

from .models import SmsDeliveryLog


@admin.register(SmsDeliveryLog)
class SmsDeliveryLogAdmin(admin.ModelAdmin):
    list_display = (
        "purpose",
        "provider",
        "status",
        "user",
        "provider_status",
        "created_at",
        "accepted_at",
    )
    list_filter = ("purpose", "provider", "status", "created_at")
    search_fields = ("user__phone", "provider_message_id")
    readonly_fields = (
        "id",
        "user",
        "recipient",
        "purpose",
        "provider",
        "status",
        "request_ip_hash",
        "provider_message_id",
        "provider_status",
        "error_code",
        "created_at",
        "accepted_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
