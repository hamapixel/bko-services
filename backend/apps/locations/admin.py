from django.contrib import admin

from .models import City, Commune, Neighborhood, Region


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "is_active")
    list_filter = ("kind", "is_active")
    search_fields = ("name",)


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "region", "is_active")
    list_filter = ("region", "is_active")
    search_fields = ("name",)
    autocomplete_fields = ("region",)


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
