from django.db import IntegrityError, transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Category, Trade

from .admin_permissions import IsPlatformAdmin


def reject_extra_fields(data, allowed):
    if not isinstance(data, dict) or set(data) - allowed:
        raise ValidationError({"detail": "Champ non autorisé."})


class AdminCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "description", "display_order", "is_active")
        read_only_fields = ("id",)

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Le nom est obligatoire.")
        queryset = Category.objects.filter(name__iexact=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Une catégorie portant ce nom existe déjà.")
        return value


class AdminTradeSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Trade
        fields = (
            "id",
            "category",
            "category_name",
            "name",
            "description",
            "display_order",
            "is_active",
        )
        read_only_fields = ("id", "category_name")

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Le nom est obligatoire.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        category = attrs.get("category") or getattr(self.instance, "category", None)
        name = attrs.get("name") or getattr(self.instance, "name", "")
        if category and name:
            queryset = Trade.objects.filter(category=category, name__iexact=name.strip())
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError(
                    {"name": "Ce métier existe déjà dans cette catégorie."}
                )
        return attrs


def save_serializer(serializer, duplicate_message):
    try:
        with transaction.atomic():
            return serializer.save()
    except IntegrityError as exc:
        raise ValidationError({"detail": duplicate_message}) from exc


@method_decorator(csrf_protect, name="dispatch")
class AdminCategoryListCreateView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        rows = Category.objects.all().order_by("display_order", "name", "id")
        return Response(AdminCategorySerializer(rows, many=True).data)

    def post(self, request):
        reject_extra_fields(
            request.data,
            {"name", "description", "display_order", "is_active"},
        )
        serializer = AdminCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = save_serializer(serializer, "Cette catégorie existe déjà.")
        return Response(
            AdminCategorySerializer(category).data,
            status=status.HTTP_201_CREATED,
        )


@method_decorator(csrf_protect, name="dispatch")
class AdminCategoryDetailView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get_object(self, pk):
        try:
            return Category.objects.get(pk=pk)
        except Category.DoesNotExist as exc:
            raise NotFound("Catégorie introuvable.") from exc

    def get(self, request, pk):
        return Response(AdminCategorySerializer(self.get_object(pk)).data)

    def patch(self, request, pk):
        reject_extra_fields(
            request.data,
            {"name", "description", "display_order", "is_active"},
        )
        category = self.get_object(pk)
        serializer = AdminCategorySerializer(category, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        category = save_serializer(serializer, "Cette catégorie existe déjà.")
        return Response(AdminCategorySerializer(category).data)


@method_decorator(csrf_protect, name="dispatch")
class AdminTradeListCreateView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        rows = Trade.objects.select_related("category").all().order_by(
            "category__display_order",
            "category__name",
            "display_order",
            "name",
            "id",
        )
        return Response(AdminTradeSerializer(rows, many=True).data)

    def post(self, request):
        reject_extra_fields(
            request.data,
            {"category", "name", "description", "display_order", "is_active"},
        )
        serializer = AdminTradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        trade = save_serializer(serializer, "Ce métier existe déjà dans cette catégorie.")
        trade = Trade.objects.select_related("category").get(pk=trade.pk)
        return Response(
            AdminTradeSerializer(trade).data,
            status=status.HTTP_201_CREATED,
        )


@method_decorator(csrf_protect, name="dispatch")
class AdminTradeDetailView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get_object(self, pk):
        try:
            return Trade.objects.select_related("category").get(pk=pk)
        except Trade.DoesNotExist as exc:
            raise NotFound("Métier introuvable.") from exc

    def get(self, request, pk):
        return Response(AdminTradeSerializer(self.get_object(pk)).data)

    def patch(self, request, pk):
        reject_extra_fields(
            request.data,
            {"category", "name", "description", "display_order", "is_active"},
        )
        trade = self.get_object(pk)
        serializer = AdminTradeSerializer(trade, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        trade = save_serializer(serializer, "Ce métier existe déjà dans cette catégorie.")
        trade = Trade.objects.select_related("category").get(pk=trade.pk)
        return Response(AdminTradeSerializer(trade).data)
