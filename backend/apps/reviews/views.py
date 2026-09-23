from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.providers.models import ProviderProfile

from .models import Review
from .serializers import CreateReviewSerializer, PublicReviewSerializer, ReviewSerializer
from .services import create_review


class ClientReviewCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not isinstance(request.data, dict) or set(request.data) - set(CreateReviewSerializer().fields):
            raise ValidationError({"detail": "Champ non autorisé."})
        serializer = CreateReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = create_review(
            pk,
            request.user,
            **serializer.validated_data,
        )
        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)


class PublicProviderReviewListView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = PublicReviewSerializer

    def get_queryset(self):
        return Review.objects.filter(
            provider_id=self.kwargs["provider_id"],
            provider__status=ProviderProfile.Status.VERIFIED,
            provider__user__role="PROVIDER",
            provider__user__is_active=True,
            provider__user__phone_verified_at__isnull=False,
        )
