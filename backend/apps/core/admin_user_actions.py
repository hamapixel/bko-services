from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.providers.models import ProviderProfile

from .admin_permissions import IsPlatformAdmin
from .admin_views import AdminUserSerializer


User = get_user_model()


class AdminUserStatusSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()


def _reject_extra_fields(data, allowed):
    if not isinstance(data, dict) or set(data) - allowed:
        raise ValidationError({"detail": "Champ non autorisé."})


def _can_change_users(user):
    return bool(user.is_superuser or user.has_perm("accounts.change_user"))


def _can_delete_users(user):
    return bool(user.is_superuser or user.has_perm("accounts.delete_user"))


def _get_locked_user(pk):
    try:
        return User.objects.select_for_update().get(pk=pk)
    except User.DoesNotExist as exc:
        raise NotFound("Utilisateur introuvable.") from exc


def _ensure_target_can_be_managed(actor, target):
    if target.pk == actor.pk:
        raise ValidationError(
            {"detail": "Vous ne pouvez pas désactiver ou supprimer votre propre compte."}
        )
    if target.is_superuser or target.role == User.Role.SUPERADMIN:
        raise ValidationError(
            {"detail": "Un compte super administrateur est protégé depuis cette interface."}
        )


def _has_business_history(user):
    ephemeral_models = {
        ("accounts", "otpcode"),
        ("accounts", "passwordresetcode"),
        ("messaging", "smsdeliverylog"),
    }

    for relation in user._meta.related_objects:
        model = relation.related_model
        model_key = (model._meta.app_label, model._meta.model_name)
        if model_key in ephemeral_models:
            continue

        accessor = relation.get_accessor_name()
        if not accessor:
            continue

        try:
            related = getattr(user, accessor)
        except model.DoesNotExist:
            continue

        if relation.one_to_one:
            return True
        if hasattr(related, "exists") and related.exists():
            return True

    return False


@method_decorator(csrf_protect, name="dispatch")
class AdminUserStatusView(APIView):
    permission_classes = [IsPlatformAdmin]

    @transaction.atomic
    def patch(self, request, pk):
        if not _can_change_users(request.user):
            raise PermissionDenied("Modification des utilisateurs non autorisée.")

        _reject_extra_fields(request.data, {"is_active"})
        serializer = AdminUserStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target = _get_locked_user(pk)
        _ensure_target_can_be_managed(request.user, target)

        next_active = serializer.validated_data["is_active"]
        if target.is_active != next_active:
            target.is_active = next_active
            target.save(update_fields=["is_active"])

        if not next_active:
            ProviderProfile.objects.filter(user=target).update(is_available=False)

        return Response(AdminUserSerializer(target).data, status=status.HTTP_200_OK)


@method_decorator(csrf_protect, name="dispatch")
class AdminUserDeleteView(APIView):
    permission_classes = [IsPlatformAdmin]

    @transaction.atomic
    def delete(self, request, pk):
        if not _can_delete_users(request.user):
            raise PermissionDenied("Suppression des utilisateurs non autorisée.")

        target = _get_locked_user(pk)
        _ensure_target_can_be_managed(request.user, target)

        if _has_business_history(target):
            raise ValidationError(
                {
                    "detail": (
                        "Ce compte possède déjà un historique BKO Services. "
                        "Désactivez-le au lieu de le supprimer afin de conserver les traces."
                    )
                }
            )

        target.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
