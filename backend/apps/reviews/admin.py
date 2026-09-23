from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("provider", "client", "rating", "service_request", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("provider__display_name", "client__phone", "service_request__title")
    readonly_fields = ("id", "service_request", "client", "provider", "rating", "comment", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
