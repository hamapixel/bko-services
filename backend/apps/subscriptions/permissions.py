from rest_framework.permissions import BasePermission

from .services import can_manage_subscriptions


class CanManageSubscriptions(BasePermission):
    def has_permission(self, request, view):
        return can_manage_subscriptions(request.user)
