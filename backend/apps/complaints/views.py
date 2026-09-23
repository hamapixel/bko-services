from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import Complaint
from .permissions import IsComplaintAdmin
from .serializers import (
    AdminComplaintSerializer,
    ComplaintCreateSerializer,
    ComplaintSerializer,
    ComplaintTransitionSerializer,
)
from .services import create_complaint, transition_complaint


@method_decorator(csrf_protect, name="dispatch")
class ComplaintListCreateView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ComplaintSerializer
    throttle_scope = "complaint_create"

    def get_throttles(self):
        return [ScopedRateThrottle()] if self.request.method == "POST" else []

    def get_queryset(self):
        return (
            Complaint.objects.filter(reporter=self.request.user)
            .select_related("service_request")
            .prefetch_related("status_history")
        )

    def post(self, request):
        if not isinstance(request.data, dict) or set(request.data) - set(ComplaintCreateSerializer().fields):
            raise ValidationError({"detail": "Champ non autorisé."})

        serializer = ComplaintCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        complaint = create_complaint(
            request.user,
            **serializer.validated_data,
        )
        return Response(
            ComplaintSerializer(complaint).data,
            status=status.HTTP_201_CREATED,
        )


class ComplaintDetailView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ComplaintSerializer
    lookup_field = "pk"

    def get_queryset(self):
        return (
            Complaint.objects.filter(reporter=self.request.user)
            .select_related("service_request")
            .prefetch_related("status_history")
        )


class AdminComplaintListView(ListAPIView):
    permission_classes = [IsComplaintAdmin]
    serializer_class = AdminComplaintSerializer

    def get_queryset(self):
        return (
            Complaint.objects.all()
            .select_related("reporter", "service_request")
            .prefetch_related("status_history")
        )


class AdminComplaintDetailView(RetrieveAPIView):
    permission_classes = [IsComplaintAdmin]
    serializer_class = AdminComplaintSerializer
    lookup_field = "pk"

    def get_queryset(self):
        return (
            Complaint.objects.all()
            .select_related("reporter", "service_request")
            .prefetch_related("status_history")
        )


@method_decorator(csrf_protect, name="dispatch")
class AdminComplaintTransitionView(APIView):
    permission_classes = [IsComplaintAdmin]

    def post(self, request, pk):
        if not isinstance(request.data, dict) or set(request.data) - set(ComplaintTransitionSerializer().fields):
            raise ValidationError({"detail": "Champ non autorisé."})

        serializer = ComplaintTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        complaint = transition_complaint(
            pk,
            request.user,
            target_status=serializer.validated_data["status"],
            note=serializer.validated_data.get("note", ""),
        )
        return Response(AdminComplaintSerializer(complaint).data)
