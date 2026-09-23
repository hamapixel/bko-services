from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError

from .models import ProviderProfile, ProviderReview
from .review import can_review_providers, review_provider


class ReviewInline(admin.TabularInline):
    model = ProviderReview
    extra = 0
    readonly_fields = ("reviewer", "decision", "note", "created_at")

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ProviderProfile)
class ProviderProfileAdmin(admin.ModelAdmin):
    list_display = ("display_name", "status", "user", "identity_checked", "is_available", "created_at")
    list_filter = ("status", "identity_checked")
    search_fields = ("display_name", "legal_name", "user__phone")
    list_select_related = ("user",)
    autocomplete_fields = ("trades", "service_areas")
    readonly_fields = ("user", "status", "is_available", "verified_at", "verified_by", "created_at", "updated_at")
    inlines = (ReviewInline,)
    actions = ("approve_selected", "reject_selected", "suspend_selected", "reopen_selected")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        fields = self.readonly_fields
        if obj and obj.status == ProviderProfile.Status.VERIFIED:
            fields += ("legal_name", "display_name", "description", "trades", "service_areas", "identity_checked")
        return fields

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not can_review_providers(request.user):
            for name in self.actions:
                actions.pop(name, None)
        return actions

    def save_model(self, request, obj, form, change):
        if change and set(form.changed_data) & {"legal_name", "display_name", "description", "trades", "service_areas"}:
            obj.identity_checked = False
            obj.review_note = ""
        super().save_model(request, obj, form, change)

    def _apply_decision(self, request, queryset, decision):
        success = 0
        for profile_id in queryset.values_list("pk", flat=True):
            try:
                review_provider(profile_id, request.user, decision)
            except (ValidationError, PermissionDenied) as exc:
                self.message_user(request, f"Dossier {profile_id} : {exc}", level=messages.WARNING)
            else:
                success += 1
        if success:
            self.message_user(request, f"{success} dossier(s) traité(s).", level=messages.SUCCESS)

    @admin.action(description="Approuver après contrôle d'identité")
    def approve_selected(self, request, queryset):
        self._apply_decision(request, queryset, ProviderReview.Decision.APPROVED)

    @admin.action(description="Refuser les dossiers sélectionnés")
    def reject_selected(self, request, queryset):
        self._apply_decision(request, queryset, ProviderReview.Decision.REJECTED)

    @admin.action(description="Suspendre les prestataires sélectionnés")
    def suspend_selected(self, request, queryset):
        self._apply_decision(request, queryset, ProviderReview.Decision.SUSPENDED)

    @admin.action(description="Rouvrir les dossiers sélectionnés")
    def reopen_selected(self, request, queryset):
        self._apply_decision(request, queryset, ProviderReview.Decision.REOPENED)
