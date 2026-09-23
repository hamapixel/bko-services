import uuid

from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny

from .models import City, Commune, Neighborhood
from .serializers import CitySerializer, CommuneSerializer, NeighborhoodSerializer


def optional_uuid(request, key):
    raw_value = request.query_params.get(key)
    if raw_value is None:
        return None
    try:
        return uuid.UUID(raw_value)
    except (ValueError, AttributeError, TypeError):
        raise ValidationError({key: "Identifiant UUID invalide."})


class CityListView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CitySerializer
    queryset = City.objects.filter(is_active=True)


class CommuneListView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CommuneSerializer

    def get_queryset(self):
        queryset = Commune.objects.filter(is_active=True, city__is_active=True)
        city_id = optional_uuid(self.request, "city")
        return queryset.filter(city_id=city_id) if city_id else queryset


class NeighborhoodListView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = NeighborhoodSerializer

    def get_queryset(self):
        queryset = Neighborhood.objects.filter(is_active=True, commune__is_active=True, commune__city__is_active=True)
        commune_id = optional_uuid(self.request, "commune")
        return queryset.filter(commune_id=commune_id) if commune_id else queryset
