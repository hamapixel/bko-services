from rest_framework.permissions import BasePermission


def is_platform_admin(user):
    return bool(
        user
        and user.is_authenticated
        and user.is_active
        and user.is_staff
        and (
            user.is_superuser
            or user.role in {user.Role.ADMIN, user.Role.SUPERADMIN}
        )
    )


class IsPlatformAdmin(BasePermission):
    def has_permission(self, request, view):
        return is_platform_admin(request.user)


class CanViewUsers(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            is_platform_admin(user)
            and (
                user.is_superuser
                or user.has_perm("accounts.view_user")
            )
        )


class CanViewServiceRequests(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            is_platform_admin(user)
            and (
                user.is_superuser
                or user.has_perm("requests.view_servicerequest")
            )
        )


class CanReviewProviders(BasePermission):
    def has_permission(self, request, view):
        from apps.providers.review import can_review_providers
        return can_review_providers(request.user)
