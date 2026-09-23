from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email")}),
        (_("Permissions"), {"fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Important dates"), {"fields": ("last_login", "date_joined", "phone_verified_at")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("phone", "password1", "password2", "role")}),
    )
    list_display = ("phone", "role", "is_active", "is_staff", "phone_verified_at")
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    search_fields = ("phone", "first_name", "last_name")
    ordering = ("phone",)
    readonly_fields = ("last_login", "date_joined", "phone_verified_at")
