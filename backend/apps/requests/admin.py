from django.contrib import admin

from .models import RequestStatusHistory, ServiceRequest


class StatusHistoryInline(admin.TabularInline):
    model = RequestStatusHistory
    extra = 0
    readonly_fields = ("actor", "previous_status", "new_status", "created_at")

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "status", "priority", "client", "created_at")
    list_filter = ("status", "priority", "created_at")
    search_fields = ("id", "title", "client__phone")
    list_select_related = ("client",)
    readonly_fields = (
        "id", "client", "trade", "neighborhood", "title", "description", "address_detail",
        "priority", "status", "created_at", "updated_at",
    )
    inlines = (StatusHistoryInline,)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
