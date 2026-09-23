from django.urls import path

from apps.requests.offer_views import ProviderOfferAcceptView, ProviderOfferDetailView, ProviderOfferListView
from apps.requests.workflow_views import (
    ProviderInterventionDetailView,
    ProviderInterventionListView,
    ProviderInterventionTransitionView,
)

from .views import ApplicationView, AvailabilityView, PublicProviderListView

urlpatterns = [
    path("", PublicProviderListView.as_view(), name="public-providers"),
    path("application/", ApplicationView.as_view(), name="provider-application"),
    path("availability/", AvailabilityView.as_view(), name="provider-availability"),
    path("offers/", ProviderOfferListView.as_view(), name="provider-offers"),
    path("offers/<uuid:pk>/", ProviderOfferDetailView.as_view(), name="provider-offer-detail"),
    path("offers/<uuid:pk>/accept/", ProviderOfferAcceptView.as_view(), name="provider-offer-accept"),
    path("interventions/", ProviderInterventionListView.as_view(), name="provider-interventions"),
    path("interventions/<uuid:pk>/", ProviderInterventionDetailView.as_view(), name="provider-intervention-detail"),
    path(
        "interventions/<uuid:pk>/transition/",
        ProviderInterventionTransitionView.as_view(),
        name="provider-intervention-transition",
    ),
]
