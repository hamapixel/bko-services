import uuid

from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny

from .models import Category, Trade
from .serializers import CategorySerializer, TradeSerializer


class CategoryListView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CategorySerializer
    queryset = Category.objects.filter(is_active=True)


class TradeListView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = TradeSerializer

    def get_queryset(self):
        queryset = Trade.objects.filter(is_active=True, category__is_active=True)
        category = self.request.query_params.get("category")
        if category is None:
            return queryset
        try:
            category_id = uuid.UUID(category)
        except (ValueError, AttributeError, TypeError):
            raise ValidationError({"category": "Identifiant UUID invalide."})
        return queryset.filter(category_id=category_id)
