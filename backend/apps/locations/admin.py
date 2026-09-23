from django.contrib import admin

from .models import City, Commune, Neighborhood


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Commune)
class CommuneAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "is_active")
    list_filter = ("city", "is_active")
    search_fields = ("name", "city__name")
    list_select_related = ("city",)
    autocomplete_fields = ("city",)


@admin.register(Neighborhood)
class NeighborhoodAdmin(admin.ModelAdmin):
    list_display = ("name", "commune", "is_active")
    list_filter = ("commune__city", "is_active")
    search_fields = ("name", "commune__name")
    list_select_related = ("commune", "commune__city")
    autocomplete_fields = ("commune",)
