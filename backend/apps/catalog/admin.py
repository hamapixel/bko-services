from django.contrib import admin

from .models import Category, Trade


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "display_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "display_order", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name", "category__name")
    list_select_related = ("category",)
    autocomplete_fields = ("category",)
