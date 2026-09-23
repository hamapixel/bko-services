from rest_framework import serializers

from .models import Category, Trade


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "description")


class TradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trade
        fields = ("id", "name", "description", "category")
