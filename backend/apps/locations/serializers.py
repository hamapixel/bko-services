from rest_framework import serializers

from .models import City, Commune, Neighborhood


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ("id", "name")


class CommuneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commune
        fields = ("id", "name", "city")


class NeighborhoodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Neighborhood
        fields = ("id", "name", "commune")
