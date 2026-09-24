from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import Http404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ProviderProfile
from .serializers import ApplicationSerializer, AvailabilitySerializer, OwnProviderSerializer, PublicProviderSerializer


def reject_extra_fields(data, allowed):
    if not isinstance(data, dict) or set(data) - allowed:
        raise ValidationError({"detail": "Champ non autorisé."})


@method_decorator(csrf_protect, name="dispatch")
class ApplicationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = ProviderProfile.objects.get(user=request.user)
        except ProviderProfile.DoesNotExist as exc:
            raise Http404 from exc
        return Response(OwnProviderSerializer(profile).data)

    @transaction.atomic
    def post(self, request):
        reject_extra_fields(request.data, set(ApplicationSerializer().fields))
        user = get_user_model().objects.select_for_update().get(pk=request.user.pk)
        if user.role != user.Role.CLIENT or not user.is_active or user.phone_verified_at is None:
            raise PermissionDenied("Un compte client avec téléphone vérifié est nécessaire.")
        if ProviderProfile.objects.filter(user=user).exists():
            raise ValidationError({"detail": "Un dossier existe déjà pour ce compte."})
        serializer = ApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save(user=user)
        return Response(OwnProviderSerializer(profile).data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def patch(self, request):
        reject_extra_fields(request.data, set(ApplicationSerializer().fields))
        if not request.data:
            raise ValidationError({"detail": "Indiquez au moins un champ à modifier."})
        try:
            profile = ProviderProfile.objects.select_for_update().get(user=request.user)
        except ProviderProfile.DoesNotExist as exc:
            raise Http404 from exc
        if profile.status not in (profile.Status.PENDING, profile.Status.REJECTED) or request.user.role != request.user.Role.CLIENT:
            raise PermissionDenied("Ce dossier ne peut plus être modifié par le candidat.")
        serializer = ApplicationSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # Any applicant edit invalidates a previously completed identity check.
        profile.status = profile.Status.PENDING
        profile.identity_checked = False
        profile.review_note = ""
        profile.save(update_fields=["status", "identity_checked", "review_note", "updated_at"])
        return Response(OwnProviderSerializer(profile).data)


@method_decorator(csrf_protect, name="dispatch")
class AvailabilityView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def patch(self, request):
        reject_extra_fields(request.data, set(AvailabilitySerializer().fields))
        serializer = AvailabilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            profile = ProviderProfile.objects.select_for_update().get(user=request.user)
        except ProviderProfile.DoesNotExist as exc:
            raise Http404 from exc
        user = get_user_model().objects.get(pk=request.user.pk)
        if profile.status != profile.Status.VERIFIED or user.role != user.Role.PROVIDER or not user.is_active:
            raise PermissionDenied("Seul un prestataire vérifié peut modifier sa disponibilité.")
        if serializer.validated_data["is_available"]:
            if user.phone_verified_at is None:
                raise ValidationError({"detail": "Le téléphone doit être vérifié."})
            if not profile.trades.filter(is_active=True, category__is_active=True).exists() or not profile.service_areas.filter(
                is_active=True, commune__is_active=True, commune__city__is_active=True, commune__city__region__is_active=True
            ).exists():
                raise ValidationError({"detail": "Un métier et un quartier actifs sont nécessaires."})
        profile.is_available = serializer.validated_data["is_available"]
        profile.save(update_fields=["is_available", "updated_at"])
        return Response({"is_available": profile.is_available})


class PublicProviderListView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = PublicProviderSerializer
    queryset = ProviderProfile.objects.filter(
        status=ProviderProfile.Status.VERIFIED,
        user__role="PROVIDER",
        user__is_active=True,
        user__phone_verified_at__isnull=False,
        trades__is_active=True,
        trades__category__is_active=True,
        service_areas__is_active=True,
        service_areas__commune__is_active=True,
        service_areas__commune__city__is_active=True,
        service_areas__commune__city__region__is_active=True,
    ).distinct()
