from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .models import ServiceRequest
from .serializers import CreateRequestSerializer, OwnRequestSerializer
from .services import create_service_request


@method_decorator(csrf_protect, name="dispatch")
class ClientRequestListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OwnRequestSerializer
    throttle_scope = "request_create"

    def get_throttles(self):
        return [ScopedRateThrottle()] if self.request.method == "POST" else []

    def get_queryset(self):
        return (
            ServiceRequest.objects.filter(client=self.request.user)
            .select_related("assigned_provider__user")
            .prefetch_related("status_history")
        )

    def post(self, request):
        if not isinstance(request.data, dict) or set(request.data) - set(CreateRequestSerializer().fields):
            raise ValidationError({"detail": "Champ non autorisé."})
        serializer = CreateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service_request = create_service_request(request.user.pk, **serializer.validated_data)
        return Response(OwnRequestSerializer(service_request).data, status=status.HTTP_201_CREATED)


class ClientRequestDetailView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OwnRequestSerializer
    lookup_field = "pk"

    def get_queryset(self):
        return (
            ServiceRequest.objects.filter(client=self.request.user)
            .select_related("assigned_provider__user")
            .prefetch_related("status_history")
        )
