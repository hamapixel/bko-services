from django.contrib import admin

from .models import Complaint, ComplaintStatusHistory


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = (
        "service_request",
        "category",
        "status",
        "reporter",
        "created_at",
        "resolved_at",
    )
    list_filter = ("category", "status", "created_at")
    search_fields = ("service_request__id", "reporter__phone")
    readonly_fields = (
        "id",
        "service_request",
        "reporter",
        "category",
        "description",
        "status",
        "previous_request_status",
        "resolution_note",
        "created_at",
        "updated_at",
        "resolved_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ComplaintStatusHistory)
class ComplaintStatusHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "complaint",
        "previous_status",
        "new_status",
        "actor",
        "created_at",
    )
    readonly_fields = (
        "id",
        "complaint",
        "actor",
        "previous_status",
        "new_status",
        "note",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
