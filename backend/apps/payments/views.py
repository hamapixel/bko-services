import json

from django.conf import settings
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
from .wave import complete_wave_checkout, start_wave_payment, verify_wave_signature, wave_is_configured


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
        if settings.PAYMENT_PROVIDER.upper() == "WAVE":
            return Response(
                {"detail": "Utilisez le parcours de paiement Wave."},
                status=status.HTTP_400_BAD_REQUEST,
            )
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


class PaymentMethodsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"wave": wave_is_configured(), "orange_money": False})


@method_decorator(csrf_protect, name="dispatch")
class WaveCheckoutView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "payment_create"

    def get_throttles(self):
        return [ScopedRateThrottle()]

    def post(self, request):
        reject_extra_fields(request.data, set(PaymentCreateSerializer().fields))
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payment = start_wave_payment(request.user, **serializer.validated_data)
        except PaymentConfigurationError:
            return Response({"detail": "Paiement Wave indisponible."}, status=503)
        return Response(PaymentTransactionSerializer(payment).data)


@method_decorator(csrf_exempt, name="dispatch")
class WaveWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        raw_body = request.body
        try:
            verify_wave_signature(raw_body, request.headers.get("Wave-Signature", ""))
        except PaymentConfigurationError:
            return Response({"detail": "Webhook Wave indisponible."}, status=503)
        except InvalidPaymentSignature:
            return Response({"detail": "Signature Wave invalide."}, status=401)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ParseError("Payload Wave invalide.") from exc
        if not isinstance(payload, dict):
            raise ParseError("Payload Wave invalide.")
        result = complete_wave_checkout(payload, raw_body)
        return Response(
            {"result": "ignored" if result is None else result[1]},
            status=200 if result is None else result[2],
        )


@method_decorator(csrf_exempt, name="dispatch")
class PaymentWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        if settings.PAYMENT_PROVIDER.upper() == "WAVE":
            return Response({"detail": "Webhook générique indisponible."}, status=503)
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
            expected_provider=settings.PAYMENT_PROVIDER,
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

    def get_queryset(self):
        queryset = PaymentTransaction.objects.all().select_related(
            "provider",
            "plan",
            "subscription",
        )
        payment_status = self.request.query_params.get("status")
        if payment_status:
            if payment_status not in PaymentTransaction.Status.values:
                raise ValidationError({"status": "Statut de paiement invalide."})
            queryset = queryset.filter(status=payment_status)
        return queryset


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
