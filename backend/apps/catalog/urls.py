from django.urls import path

from .views import CategoryListView, TradeListView

urlpatterns = [
    path("categories/", CategoryListView.as_view(), name="catalog-categories"),
    path("trades/", TradeListView.as_view(), name="catalog-trades"),
]
