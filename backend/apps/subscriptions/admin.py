from django.contrib import admin

from .models import ProviderSubscription, SubscriptionHistory, SubscriptionPlan


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "price_xof",
        "duration_days",
        "can_receive_requests",
        "can_receive_urgent_requests",
        "max_active_jobs",
        "is_active",
    )
    list_filter = (
        "is_active",
        "can_receive_requests",
        "can_receive_urgent_requests",
    )
    search_fields = ("code", "name")
    ordering = ("display_order", "price_xof", "name")


@admin.register(ProviderSubscription)
class ProviderSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "provider",
        "plan",
        "status",
        "starts_at",
        "ends_at",
        "updated_at",
    )
    list_filter = ("status", "plan")
    search_fields = ("provider__display_name", "provider__user__phone")
    readonly_fields = (
        "id",
        "provider",
        "plan",
        "status",
        "starts_at",
        "ends_at",
        "activated_by",
        "cancelled_at",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SubscriptionHistory)
class SubscriptionHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "subscription",
        "action",
        "plan_code",
        "starts_at",
        "ends_at",
        "created_at",
    )
    list_filter = ("action",)
    readonly_fields = (
        "id",
        "subscription",
        "actor",
        "action",
        "plan_code",
        "plan_name",
        "starts_at",
        "ends_at",
        "note",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
