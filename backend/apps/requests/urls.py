from django.urls import path

from .views import ClientRequestDetailView, ClientRequestListView
from apps.reviews.views import ClientReviewCreateView

from .workflow_views import ClientRequestConfirmView

urlpatterns = [
    path("", ClientRequestListView.as_view(), name="client-requests"),
    path("<uuid:pk>/", ClientRequestDetailView.as_view(), name="client-request-detail"),
    path("<uuid:pk>/confirm/", ClientRequestConfirmView.as_view(), name="client-request-confirm"),
    path("<uuid:pk>/review/", ClientReviewCreateView.as_view(), name="client-request-review"),
]
