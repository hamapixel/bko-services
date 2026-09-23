from django.http import Http404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.providers.models import ProviderProfile

from .models import ProviderSubscription, SubscriptionPlan
from .permissions import CanManageSubscriptions
from .serializers import (
    ActivateSubscriptionSerializer,
    AdminProviderSubscriptionSerializer,
    CancelSubscriptionSerializer,
    ProviderSubscriptionSerializer,
    PublicSubscriptionPlanSerializer,
    RenewSubscriptionSerializer,
    SubscriptionPlanSerializer,
    validate_plan_attributes,
)
from .services import (
    activate_subscription,
    cancel_subscription,
    renew_subscription,
)


def reject_extra_fields(data, allowed):
    if not isinstance(data, dict) or set(data) - allowed:
        raise ValidationError({"detail": "Champ non autorisé."})


class PublicPlanListView(ListAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = PublicSubscriptionPlanSerializer
    queryset = SubscriptionPlan.objects.filter(is_active=True)


class MySubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != request.user.Role.PROVIDER or not request.user.is_active:
            raise PermissionDenied("Espace réservé aux prestataires actifs.")

        try:
            provider = ProviderProfile.objects.get(user=request.user)
        except ProviderProfile.DoesNotExist as exc:
            raise Http404 from exc

        subscription = (
            ProviderSubscription.objects.filter(provider=provider)
            .select_related("plan")
            .prefetch_related("history")
            .first()
        )
        return Response(
            {
                "subscription": (
                    ProviderSubscriptionSerializer(subscription).data
                    if subscription
                    else None
                )
            }
        )


@method_decorator(csrf_protect, name="dispatch")
class AdminPlanListCreateView(ListAPIView):
    permission_classes = [CanManageSubscriptions]
    serializer_class = SubscriptionPlanSerializer
    queryset = SubscriptionPlan.objects.all()

    def post(self, request):
        reject_extra_fields(request.data, set(SubscriptionPlanSerializer().fields) - {"id"})
        serializer = SubscriptionPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validate_plan_attributes(serializer.validated_data)
        plan = serializer.save()
        return Response(
            SubscriptionPlanSerializer(plan).data,
            status=status.HTTP_201_CREATED,
        )


@method_decorator(csrf_protect, name="dispatch")
class AdminPlanDetailView(APIView):
    permission_classes = [CanManageSubscriptions]

    def patch(self, request, pk):
        reject_extra_fields(request.data, set(SubscriptionPlanSerializer().fields) - {"id"})
        try:
            plan = SubscriptionPlan.objects.get(pk=pk)
        except SubscriptionPlan.DoesNotExist as exc:
            raise Http404 from exc
        serializer = SubscriptionPlanSerializer(plan, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        combined = {
            "can_receive_requests": serializer.validated_data.get(
                "can_receive_requests",
                plan.can_receive_requests,
            ),
            "can_receive_urgent_requests": serializer.validated_data.get(
                "can_receive_urgent_requests",
                plan.can_receive_urgent_requests,
            ),
        }
        validate_plan_attributes(combined)
        serializer.save()
        return Response(SubscriptionPlanSerializer(plan).data)


class AdminSubscriptionListView(ListAPIView):
    permission_classes = [CanManageSubscriptions]
    serializer_class = AdminProviderSubscriptionSerializer
    queryset = (
        ProviderSubscription.objects.all()
        .select_related("provider", "plan")
        .prefetch_related("history")
    )


class AdminProviderSubscriptionView(APIView):
    permission_classes = [CanManageSubscriptions]

    def get(self, request, provider_id):
        try:
            provider = ProviderProfile.objects.get(pk=provider_id)
        except ProviderProfile.DoesNotExist as exc:
            raise Http404 from exc
        subscription = (
            ProviderSubscription.objects.filter(provider=provider)
            .select_related("provider", "plan")
            .prefetch_related("history")
            .first()
        )
        return Response(
            {
                "subscription": (
                    AdminProviderSubscriptionSerializer(subscription).data
                    if subscription
                    else None
                )
            }
        )


@method_decorator(csrf_protect, name="dispatch")
class AdminActivateSubscriptionView(APIView):
    permission_classes = [CanManageSubscriptions]

    def post(self, request, provider_id):
        reject_extra_fields(request.data, set(ActivateSubscriptionSerializer().fields))
        serializer = ActivateSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscription = activate_subscription(
            provider_id,
            request.user,
            **serializer.validated_data,
        )
        return Response(
            AdminProviderSubscriptionSerializer(subscription).data,
            status=status.HTTP_201_CREATED,
        )


@method_decorator(csrf_protect, name="dispatch")
class AdminRenewSubscriptionView(APIView):
    permission_classes = [CanManageSubscriptions]

    def post(self, request, pk):
        reject_extra_fields(request.data, set(RenewSubscriptionSerializer().fields))
        serializer = RenewSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscription = renew_subscription(
            pk,
            request.user,
            **serializer.validated_data,
        )
        return Response(AdminProviderSubscriptionSerializer(subscription).data)


@method_decorator(csrf_protect, name="dispatch")
class AdminCancelSubscriptionView(APIView):
    permission_classes = [CanManageSubscriptions]

    def post(self, request, pk):
        reject_extra_fields(request.data, set(CancelSubscriptionSerializer().fields))
        serializer = CancelSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscription = cancel_subscription(
            pk,
            request.user,
            **serializer.validated_data,
        )
        return Response(AdminProviderSubscriptionSerializer(subscription).data)
