from rest_framework import serializers, status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .acceptance import accept_offer
from .models import ServiceOffer, ServiceRequest


class ProviderOfferSerializer(serializers.ModelSerializer):
    request_id = serializers.UUIDField(source="service_request_id", read_only=True)
    trade_id = serializers.UUIDField(source="service_request.trade_id", read_only=True)
    trade_name = serializers.CharField(source="service_request.trade.name", read_only=True)
    neighborhood_id = serializers.UUIDField(source="service_request.neighborhood_id", read_only=True)
    neighborhood_name = serializers.CharField(source="service_request.neighborhood.name", read_only=True)
    commune_name = serializers.CharField(source="service_request.neighborhood.commune.name", read_only=True)
    priority = serializers.ChoiceField(source="service_request.priority", choices=ServiceRequest.Priority.choices, read_only=True)

    class Meta:
        model = ServiceOffer
        fields = (
            "id", "request_id", "trade_id", "trade_name",
            "neighborhood_id", "neighborhood_name", "commune_name",
            "priority", "status", "created_at",
        )
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
        service_request__neighborhood__commune__city__region__is_active=True,
        provider__user=user,
        provider__status="VERIFIED",
        provider__is_available=True,
        provider__user__is_active=True,
        provider__user__role="PROVIDER",
        provider__user__phone_verified_at__isnull=False,
    ).select_related(
        "service_request__trade",
        "service_request__neighborhood__commune",
    )


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


class ProviderOfferAcceptView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        offer, service_request = accept_offer(pk, request.user)
        return Response(
            {
                "id": str(offer.pk),
                "request_id": str(service_request.pk),
                "status": offer.status,
                "request_status": service_request.status,
                "assigned_provider_id": str(service_request.assigned_provider_id),
            },
            status=status.HTTP_200_OK,
        )
