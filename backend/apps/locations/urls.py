from django.urls import path

from .views import CityListView, CommuneListView, NeighborhoodListView, RegionListView

urlpatterns = [
    path("regions/", RegionListView.as_view(), name="location-regions"),
    path("cities/", CityListView.as_view(), name="location-cities"),
    path("communes/", CommuneListView.as_view(), name="location-communes"),
    path("neighborhoods/", NeighborhoodListView.as_view(), name="location-neighborhoods"),
]
