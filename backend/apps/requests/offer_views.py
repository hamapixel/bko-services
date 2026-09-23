from rest_framework import serializers
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated

from .models import ServiceOffer, ServiceRequest


class ProviderOfferSerializer(serializers.ModelSerializer):
    request_id = serializers.UUIDField(source="service_request_id", read_only=True)
    trade_id = serializers.UUIDField(source="service_request.trade_id", read_only=True)
    neighborhood_id = serializers.UUIDField(source="service_request.neighborhood_id", read_only=True)
    priority = serializers.ChoiceField(source="service_request.priority", choices=ServiceRequest.Priority.choices, read_only=True)

    class Meta:
        model = ServiceOffer
        fields = ("id", "request_id", "trade_id", "neighborhood_id", "priority", "status", "created_at")
        read_only_fields = fields


def own_pending_offers(user):
    return ServiceOffer.objects.filter(
        status=ServiceOffer.Status.PENDING,
        service_request__status=ServiceRequest.Status.OFFERED,
        service_request__trade__is_active=True,
        service_request__trade__category__is_active=True,
        service_request__neighborhood__is_active=True,
        service_request__neighborhood__commune__is_active=True,
        service_request__neighborhood__commune__city__is_active=True,
        provider__user=user,
        provider__status="VERIFIED",
        provider__is_available=True,
        provider__user__is_active=True,
        provider__user__role="PROVIDER",
        provider__user__phone_verified_at__isnull=False,
    ).select_related("service_request")


class ProviderOfferListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProviderOfferSerializer

    def get_queryset(self):
        return own_pending_offers(self.request.user)


class ProviderOfferDetailView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProviderOfferSerializer

    def get_queryset(self):
        return own_pending_offers(self.request.user)
