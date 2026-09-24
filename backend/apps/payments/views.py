import json

from django.http import Http404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from rest_framework import status
from rest_framework.exceptions import ParseError, ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import PaymentTransaction
from .permissions import CanManagePayments
from .serializers import (
    AdminPaymentTransactionSerializer,
    PaymentCreateSerializer,
    PaymentTransactionSerializer,
    PaymentWebhookSerializer,
)
from .services import (
    InvalidPaymentSignature,
    PaymentConfigurationError,
    create_payment_transaction,
    process_verified_webhook,
    retry_fulfillment,
    verify_webhook_signature,
)


def reject_extra_fields(data, allowed):
    if not isinstance(data, dict) or set(data) - allowed:
        raise ValidationError({"detail": "Champ non autorisé."})


@method_decorator(csrf_protect, name="dispatch")
class PaymentListCreateView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentTransactionSerializer
    throttle_scope = "payment_create"

    def get_throttles(self):
        return [ScopedRateThrottle()] if self.request.method == "POST" else []

    def get_queryset(self):
        user = self.request.user
        if user.role != user.Role.PROVIDER or not user.is_active:
            return PaymentTransaction.objects.none()
        return PaymentTransaction.objects.filter(
            provider__user=user
        ).select_related("plan", "subscription")

    def post(self, request):
        reject_extra_fields(request.data, set(PaymentCreateSerializer().fields))
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment, created = create_payment_transaction(
            request.user,
            **serializer.validated_data,
        )
        return Response(
            PaymentTransactionSerializer(payment).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class PaymentDetailView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentTransactionSerializer
    lookup_field = "pk"

    def get_queryset(self):
        user = self.request.user
        if user.role != user.Role.PROVIDER or not user.is_active:
            return PaymentTransaction.objects.none()
        return PaymentTransaction.objects.filter(
            provider__user=user
        ).select_related("plan", "subscription")


@method_decorator(csrf_exempt, name="dispatch")
class PaymentWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        raw_body = request.body
        try:
            verify_webhook_signature(
                raw_body,
                request.headers.get("X-BKO-Payment-Signature", ""),
            )
        except PaymentConfigurationError:
            return Response(
                {"detail": "Webhook de paiement indisponible."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except InvalidPaymentSignature:
            return Response(
                {"detail": "Signature invalide."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ParseError("Payload JSON invalide.") from exc

        reject_extra_fields(payload, set(PaymentWebhookSerializer().fields))
        serializer = PaymentWebhookSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        payment, result, response_status = process_verified_webhook(
            serializer.validated_data,
            raw_body,
        )
        return Response(
            {
                "result": result,
                "transaction": PaymentTransactionSerializer(payment).data,
            },
            status=response_status,
        )


class AdminPaymentListView(ListAPIView):
    permission_classes = [CanManagePayments]
    serializer_class = AdminPaymentTransactionSerializer
    queryset = PaymentTransaction.objects.all().select_related(
        "provider",
        "plan",
        "subscription",
    )


class AdminPaymentDetailView(RetrieveAPIView):
    permission_classes = [CanManagePayments]
    serializer_class = AdminPaymentTransactionSerializer
    queryset = PaymentTransaction.objects.all().select_related(
        "provider",
        "plan",
        "subscription",
    )
    lookup_field = "pk"


@method_decorator(csrf_protect, name="dispatch")
class AdminRetryFulfillmentView(APIView):
    permission_classes = [CanManagePayments]

    def post(self, request, pk):
        if request.data not in ({}, None):
            reject_extra_fields(request.data, set())
        payment = retry_fulfillment(pk, request.user)
        return Response(AdminPaymentTransactionSerializer(payment).data)
