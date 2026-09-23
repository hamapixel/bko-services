from django.urls import path

from .views import ApplicationView, AvailabilityView, PublicProviderListView

urlpatterns = [
    path("", PublicProviderListView.as_view(), name="public-providers"),
    path("application/", ApplicationView.as_view(), name="provider-application"),
    path("availability/", AvailabilityView.as_view(), name="provider-availability"),
]
