from django.urls import path

from .views import ClientRequestDetailView, ClientRequestListView

urlpatterns = [
    path("", ClientRequestListView.as_view(), name="client-requests"),
    path("<uuid:pk>/", ClientRequestDetailView.as_view(), name="client-request-detail"),
]
