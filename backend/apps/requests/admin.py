from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError

from .matching import can_dispatch_requests, dispatch_request
from .models import RequestStatusHistory, ServiceOffer, ServiceRequest


class StatusHistoryInline(admin.TabularInline):
    model = RequestStatusHistory
    extra = 0
    readonly_fields = ("actor", "previous_status", "new_status", "created_at")

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ServiceOfferInline(admin.TabularInline):
    model = ServiceOffer
    extra = 0
    readonly_fields = ("provider", "status", "created_at", "updated_at")

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
    inlines = (StatusHistoryInline, ServiceOfferInline)
    actions = ("start_matching",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not can_dispatch_requests(request.user):
            actions.pop("start_matching", None)
        return actions

    @admin.action(description="Créer les offres pour les demandes sélectionnées")
    def start_matching(self, request, queryset):
        offers_created = 0
        for request_id in queryset.values_list("pk", flat=True):
            try:
                offers_created += dispatch_request(request_id, request.user)
            except (ValidationError, PermissionDenied) as exc:
                self.message_user(request, f"Demande {request_id} : {exc}", level=messages.WARNING)
        self.message_user(request, f"{offers_created} offre(s) créée(s).", level=messages.SUCCESS)
