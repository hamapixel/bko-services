from rest_framework import serializers

from .models import City, Commune, Neighborhood, Region


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ("id", "name", "kind")


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ("id", "name", "region")


class CommuneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commune
        fields = ("id", "name", "city")


class NeighborhoodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Neighborhood
        fields = ("id", "name", "commune")
