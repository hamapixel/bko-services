from rest_framework import serializers, status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ServiceRequest
from .serializers import OwnRequestSerializer, ProviderInterventionSerializer
from .workflow import confirm_client_completion, transition_provider_intervention


class ProviderTransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            (ServiceRequest.Status.EN_ROUTE, "En route"),
            (ServiceRequest.Status.ARRIVED, "Arrivé"),
            (ServiceRequest.Status.IN_PROGRESS, "En cours"),
            (ServiceRequest.Status.PROVIDER_COMPLETED, "Terminée par le prestataire"),
        ]
    )


def own_provider_interventions(user):
    return (
        ServiceRequest.objects.filter(
            assigned_provider__user=user,
            assigned_provider__user__role="PROVIDER",
        )
        .select_related(
            "client",
            "trade",
            "neighborhood__commune",
            "assigned_provider__user",
        )
        .prefetch_related("status_history")
    )


class ProviderInterventionListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProviderInterventionSerializer

    def get_queryset(self):
        queryset = own_provider_interventions(self.request.user)
        raw_status = self.request.query_params.get("status")
        if raw_status:
            statuses = [value.strip() for value in raw_status.split(",") if value.strip()]
            allowed_statuses = set(ServiceRequest.Status.values)
            if not statuses or any(value not in allowed_statuses for value in statuses):
                from rest_framework.exceptions import ValidationError
                raise ValidationError({"status": "Statut d'intervention invalide."})
            queryset = queryset.filter(status__in=statuses)
        return queryset


class ProviderInterventionDetailView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProviderInterventionSerializer

    def get_queryset(self):
        return own_provider_interventions(self.request.user)


class ProviderInterventionTransitionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        serializer = ProviderTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service_request = transition_provider_intervention(
            pk,
            request.user,
            serializer.validated_data["status"],
        )
        return Response(
            ProviderInterventionSerializer(service_request).data,
            status=status.HTTP_200_OK,
        )


class ClientRequestConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        service_request = confirm_client_completion(pk, request.user)
        return Response(
            OwnRequestSerializer(service_request).data,
            status=status.HTTP_200_OK,
        )
