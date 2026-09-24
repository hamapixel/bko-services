from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.complaints.models import Complaint
from apps.payments.models import PaymentTransaction
from apps.providers.models import ProviderProfile, ProviderReview
from apps.providers.review import can_review_providers, review_provider
from apps.requests.matching import dispatch_request
from apps.requests.models import ServiceRequest
from apps.subscriptions.models import ProviderSubscription

from .admin_permissions import (
    CanViewServiceRequests,
    CanViewUsers,
    IsPlatformAdmin,
)


User = get_user_model()


def reject_extra_fields(data, allowed):
    if not isinstance(data, dict) or set(data) - allowed:
        raise ValidationError({"detail": "Champ non autorisé."})


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "phone",
            "first_name",
            "last_name",
            "email",
            "role",
            "is_active",
            "is_staff",
            "phone_verified_at",
            "date_joined",
            "last_login",
        )
        read_only_fields = fields


class AdminProviderReviewHistorySerializer(serializers.ModelSerializer):
    reviewer_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = ProviderReview
        fields = ("id", "reviewer_id", "decision", "note", "created_at")
        read_only_fields = fields


class AdminProviderSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(read_only=True)
    user_phone = serializers.CharField(source="user.phone", read_only=True)
    user_phone_verified_at = serializers.DateTimeField(
        source="user.phone_verified_at",
        read_only=True,
    )
    user_is_active = serializers.BooleanField(source="user.is_active", read_only=True)
    trade_details = serializers.SerializerMethodField()
    service_area_details = serializers.SerializerMethodField()
    reviews = AdminProviderReviewHistorySerializer(many=True, read_only=True)

    class Meta:
        model = ProviderProfile
        fields = (
            "id",
            "user_id",
            "user_phone",
            "user_phone_verified_at",
            "user_is_active",
            "legal_name",
            "display_name",
            "description",
            "trade_details",
            "service_area_details",
            "status",
            "is_available",
            "identity_checked",
            "review_note",
            "verified_at",
            "created_at",
            "updated_at",
            "reviews",
        )
        read_only_fields = fields

    def get_trade_details(self, obj):
        return [
            {"id": str(trade.pk), "name": trade.name}
            for trade in obj.trades.all().order_by("name", "id")
        ]

    def get_service_area_details(self, obj):
        return [
            {
                "id": str(area.pk),
                "name": area.name,
                "commune_name": area.commune.name,
            }
            for area in obj.service_areas.select_related("commune").all().order_by(
                "commune__name", "name", "id"
            )
        ]


class AdminProviderReviewActionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=ProviderReview.Decision.choices)
    note = serializers.CharField(max_length=500, allow_blank=False)
    identity_checked = serializers.BooleanField(required=False)


class AdminRequestListSerializer(serializers.ModelSerializer):
    trade_name = serializers.CharField(source="trade.name", read_only=True)
    neighborhood_name = serializers.CharField(source="neighborhood.name", read_only=True)
    commune_name = serializers.CharField(source="neighborhood.commune.name", read_only=True)
    client_id = serializers.UUIDField(read_only=True)
    assigned_provider_id = serializers.UUIDField(read_only=True)
    assigned_provider_display_name = serializers.CharField(
        source="assigned_provider.display_name",
        read_only=True,
        default=None,
    )

    class Meta:
        model = ServiceRequest
        fields = (
            "id",
            "trade_name",
            "neighborhood_name",
            "commune_name",
            "priority",
            "status",
            "client_id",
            "assigned_provider_id",
            "assigned_provider_display_name",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AdminRequestDetailSerializer(AdminRequestListSerializer):
    client_phone = serializers.CharField(source="client.phone", read_only=True)
    status_history = serializers.SerializerMethodField()
    offers = serializers.SerializerMethodField()

    class Meta(AdminRequestListSerializer.Meta):
        fields = AdminRequestListSerializer.Meta.fields + (
            "client_phone",
            "title",
            "description",
            "address_detail",
            "status_history",
            "offers",
        )

    def get_status_history(self, obj):
        return [
            {
                "previous_status": item.previous_status,
                "new_status": item.new_status,
                "actor_id": str(item.actor_id),
                "created_at": item.created_at,
            }
            for item in obj.status_history.all()
        ]

    def get_offers(self, obj):
        return [
            {
                "id": str(offer.pk),
                "provider_id": str(offer.provider_id),
                "provider_display_name": offer.provider.display_name,
                "status": offer.status,
                "created_at": offer.created_at,
            }
            for offer in obj.offers.all()
        ]


class AdminOverviewView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        now = timezone.now()
        active_request_statuses = [
            status_value
            for status_value in ServiceRequest.Status.values
            if status_value
            not in {
                ServiceRequest.Status.CLIENT_CONFIRMED,
                ServiceRequest.Status.CANCELLED,
            }
        ]
        return Response(
            {
                "users_total": User.objects.count(),
                "providers_pending": ProviderProfile.objects.filter(
                    status=ProviderProfile.Status.PENDING
                ).count(),
                "providers_verified": ProviderProfile.objects.filter(
                    status=ProviderProfile.Status.VERIFIED
                ).count(),
                "requests_active": ServiceRequest.objects.filter(
                    status__in=active_request_statuses
                ).count(),
                "complaints_open": Complaint.objects.filter(
                    status__in=[
                        Complaint.Status.OPEN,
                        Complaint.Status.UNDER_REVIEW,
                    ]
                ).count(),
                "payments_pending": PaymentTransaction.objects.filter(
                    status=PaymentTransaction.Status.PENDING
                ).count(),
                "payments_unfulfilled": PaymentTransaction.objects.filter(
                    status=PaymentTransaction.Status.SUCCEEDED,
                    fulfilled_at__isnull=True,
                ).count(),
                "subscriptions_effective": ProviderSubscription.objects.filter(
                    status=ProviderSubscription.Status.ACTIVE,
                    cancelled_at__isnull=True,
                    starts_at__lte=now,
                    ends_at__gt=now,
                ).count(),
            }
        )


class AdminUserListView(ListAPIView):
    permission_classes = [CanViewUsers]
    serializer_class = AdminUserSerializer

    def get_queryset(self):
        queryset = User.objects.all().order_by("-date_joined", "-id")
        role = self.request.query_params.get("role")
        if role:
            if role not in User.Role.values:
                raise ValidationError({"role": "Rôle utilisateur invalide."})
            queryset = queryset.filter(role=role)

        active = self.request.query_params.get("active")
        if active:
            if active not in {"true", "false"}:
                raise ValidationError({"active": "Valeur active invalide."})
            queryset = queryset.filter(is_active=active == "true")

        query = self.request.query_params.get("q", "").strip()
        if query:
            if len(query) > 100:
                raise ValidationError({"q": "Recherche trop longue."})
            queryset = queryset.filter(
                Q(phone__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(email__icontains=query)
            )
        return queryset


class AdminUserDetailView(RetrieveAPIView):
    permission_classes = [CanViewUsers]
    serializer_class = AdminUserSerializer
    queryset = User.objects.all()
    lookup_field = "pk"


class AdminProviderListView(ListAPIView):
    serializer_class = AdminProviderSerializer

    def get_permissions(self):
        if not can_review_providers(self.request.user):
            raise PermissionDenied("Vérification réservée aux administrateurs habilités.")
        return []

    def get_queryset(self):
        queryset = (
            ProviderProfile.objects.all()
            .select_related("user")
            .prefetch_related("trades", "service_areas__commune", "reviews")
        )
        provider_status = self.request.query_params.get("status")
        if provider_status:
            if provider_status not in ProviderProfile.Status.values:
                raise ValidationError({"status": "Statut prestataire invalide."})
            queryset = queryset.filter(status=provider_status)

        query = self.request.query_params.get("q", "").strip()
        if query:
            if len(query) > 100:
                raise ValidationError({"q": "Recherche trop longue."})
            queryset = queryset.filter(
                Q(display_name__icontains=query)
                | Q(legal_name__icontains=query)
                | Q(user__phone__icontains=query)
            )
        return queryset.order_by("-created_at", "-id")


class AdminProviderDetailView(RetrieveAPIView):
    serializer_class = AdminProviderSerializer
    lookup_field = "pk"

    def get_permissions(self):
        if not can_review_providers(self.request.user):
            raise PermissionDenied("Vérification réservée aux administrateurs habilités.")
        return []

    def get_queryset(self):
        return (
            ProviderProfile.objects.all()
            .select_related("user")
            .prefetch_related("trades", "service_areas__commune", "reviews")
        )


@method_decorator(csrf_protect, name="dispatch")
class AdminProviderReviewView(APIView):
    def get_permissions(self):
        if not can_review_providers(self.request.user):
            raise PermissionDenied("Vérification réservée aux administrateurs habilités.")
        return []

    def post(self, request, pk):
        reject_extra_fields(
            request.data,
            set(AdminProviderReviewActionSerializer().fields),
        )
        serializer = AdminProviderReviewActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            profile = ProviderProfile.objects.get(pk=pk)
        except ProviderProfile.DoesNotExist:
            from django.http import Http404
            raise Http404

        profile.review_note = serializer.validated_data["note"].strip()
        if "identity_checked" in serializer.validated_data:
            profile.identity_checked = serializer.validated_data["identity_checked"]
        profile.save(update_fields=["review_note", "identity_checked", "updated_at"])

        try:
            reviewed = review_provider(
                profile.pk,
                request.user,
                serializer.validated_data["decision"],
            )
        except Exception:
            profile.refresh_from_db()
            raise

        reviewed = (
            ProviderProfile.objects.select_related("user")
            .prefetch_related("trades", "service_areas__commune", "reviews")
            .get(pk=reviewed.pk)
        )
        return Response(AdminProviderSerializer(reviewed).data)


class AdminRequestListView(ListAPIView):
    permission_classes = [CanViewServiceRequests]
    serializer_class = AdminRequestListSerializer

    def get_queryset(self):
        queryset = (
            ServiceRequest.objects.all()
            .select_related(
                "client",
                "trade",
                "neighborhood__commune",
                "assigned_provider",
            )
        )
        raw_status = self.request.query_params.get("status")
        if raw_status:
            statuses = [value.strip() for value in raw_status.split(",") if value.strip()]
            if not statuses or any(value not in ServiceRequest.Status.values for value in statuses):
                raise ValidationError({"status": "Statut de demande invalide."})
            queryset = queryset.filter(status__in=statuses)

        priority = self.request.query_params.get("priority")
        if priority:
            if priority not in ServiceRequest.Priority.values:
                raise ValidationError({"priority": "Priorité de demande invalide."})
            queryset = queryset.filter(priority=priority)
        return queryset


class AdminRequestDetailView(RetrieveAPIView):
    permission_classes = [CanViewServiceRequests]
    serializer_class = AdminRequestDetailSerializer
    lookup_field = "pk"

    def get_queryset(self):
        return (
            ServiceRequest.objects.all()
            .select_related(
                "client",
                "trade",
                "neighborhood__commune",
                "assigned_provider",
            )
            .prefetch_related(
                "status_history",
                "offers__provider",
            )
        )


@method_decorator(csrf_protect, name="dispatch")
class AdminRequestDispatchView(APIView):
    permission_classes = [IsPlatformAdmin]

    def post(self, request, pk):
        reject_extra_fields(request.data, set())
        offers_created = dispatch_request(pk, request.user)
        service_request = (
            ServiceRequest.objects.select_related(
                "client",
                "trade",
                "neighborhood__commune",
                "assigned_provider",
            )
            .prefetch_related("status_history", "offers__provider")
            .get(pk=pk)
        )
        return Response(
            {
                "offers_created": offers_created,
                "request": AdminRequestDetailSerializer(service_request).data,
            },
            status=status.HTTP_200_OK,
        )
