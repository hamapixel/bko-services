from django.urls import path

from .views import CityListView, CommuneListView, NeighborhoodListView

urlpatterns = [
    path("cities/", CityListView.as_view(), name="location-cities"),
    path("communes/", CommuneListView.as_view(), name="location-communes"),
    path("neighborhoods/", NeighborhoodListView.as_view(), name="location-neighborhoods"),
]
