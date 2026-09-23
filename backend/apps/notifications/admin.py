from django.contrib import admin

from .models import Notification, PushSubscription


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "kind", "service_request", "read_at", "created_at")
    list_filter = ("kind", "read_at", "created_at")
    search_fields = ("recipient__phone", "title", "message")
    readonly_fields = (
        "id",
        "recipient",
        "kind",
        "title",
        "message",
        "service_request",
        "read_at",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "is_active", "failure_count", "last_success_at", "updated_at")
    list_filter = ("is_active", "updated_at")
    search_fields = ("user__phone", "endpoint")
    fields = (
        "id",
        "user",
        "endpoint",
        "is_active",
        "failure_count",
        "last_success_at",
        "created_at",
        "updated_at",
    )
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
