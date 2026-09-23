from django.urls import path

from apps.requests.offer_views import ProviderOfferAcceptView, ProviderOfferDetailView, ProviderOfferListView

from .views import ApplicationView, AvailabilityView, PublicProviderListView

urlpatterns = [
    path("", PublicProviderListView.as_view(), name="public-providers"),
    path("application/", ApplicationView.as_view(), name="provider-application"),
    path("availability/", AvailabilityView.as_view(), name="provider-availability"),
    path("offers/", ProviderOfferListView.as_view(), name="provider-offers"),
    path("offers/<uuid:pk>/", ProviderOfferDetailView.as_view(), name="provider-offer-detail"),
    path("offers/<uuid:pk>/accept/", ProviderOfferAcceptView.as_view(), name="provider-offer-accept"),
]
