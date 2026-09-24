from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.providers.models import ProviderProfile

from .models import ProviderSubscription, SubscriptionHistory, SubscriptionPlan


def can_manage_subscriptions(user):
    return bool(
        user
        and user.is_authenticated
        and user.is_active
        and user.is_staff
        and (
            user.is_superuser
            or (
                user.role == user.Role.ADMIN
                and user.has_perm("subscriptions.manage_subscriptions")
            )
        )
    )


def effective_subscription_status(subscription, at=None):
    at = at or timezone.now()
    if (
        subscription.status == ProviderSubscription.Status.ACTIVE
        and subscription.ends_at <= at
    ):
        return ProviderSubscription.Status.EXPIRED
    return subscription.status


def subscription_is_effective(subscription, *, urgent=False, at=None):
    at = at or timezone.now()
    if (
        subscription.status != ProviderSubscription.Status.ACTIVE
        or subscription.starts_at > at
        or subscription.ends_at <= at
        or not subscription.plan.can_receive_requests
    ):
        return False
    if urgent and not subscription.plan.can_receive_urgent_requests:
        return False
    return True


def provider_has_entitlement(provider_id, *, urgent=False, at=None):
    at = at or timezone.now()
    queryset = ProviderSubscription.objects.filter(
        provider_id=provider_id,
        status=ProviderSubscription.Status.ACTIVE,
        starts_at__lte=at,
        ends_at__gt=at,
        plan__can_receive_requests=True,
    )
    if urgent:
        queryset = queryset.filter(plan__can_receive_urgent_requests=True)
    return queryset.exists()


def eligible_provider_ids_queryset(*, urgent=False, at=None):
    at = at or timezone.now()
    queryset = ProviderSubscription.objects.filter(
        status=ProviderSubscription.Status.ACTIVE,
        starts_at__lte=at,
        ends_at__gt=at,
        plan__can_receive_requests=True,
    )
    if urgent:
        queryset = queryset.filter(plan__can_receive_urgent_requests=True)
    return queryset.values("provider_id")


def _record_history(subscription, *, actor, action, note=""):
    SubscriptionHistory.objects.create(
        subscription=subscription,
        actor=actor,
        action=action,
        plan_code=subscription.plan.code,
        plan_name=subscription.plan.name,
        starts_at=subscription.starts_at,
        ends_at=subscription.ends_at,
        note=note.strip(),
    )


def _expire_if_needed(subscription, *, actor=None, now=None):
    now = now or timezone.now()
    if (
        subscription.status == ProviderSubscription.Status.ACTIVE
        and subscription.ends_at <= now
    ):
        subscription.status = ProviderSubscription.Status.EXPIRED
        subscription.save(update_fields=["status", "updated_at"])
        _record_history(
            subscription,
            actor=actor,
            action=SubscriptionHistory.Action.EXPIRED,
        )
        return True
    return False


def _locked_plan(plan_id):
    try:
        return SubscriptionPlan.objects.select_for_update().get(
            pk=plan_id,
            is_active=True,
        )
    except SubscriptionPlan.DoesNotExist as exc:
        raise NotFound("Plan introuvable ou inactif.") from exc


def _locked_provider(provider_id):
    try:
        return (
            ProviderProfile.objects.select_for_update()
            .select_related("user")
            .get(pk=provider_id)
        )
    except ProviderProfile.DoesNotExist as exc:
        raise NotFound("Prestataire introuvable.") from exc


def _validate_provider_for_subscription(provider):
    user = provider.user
    if (
        provider.status != ProviderProfile.Status.VERIFIED
        or not user.is_active
        or user.role != user.Role.PROVIDER
        or user.phone_verified_at is None
    ):
        raise ValidationError(
            {"provider": "Le prestataire doit être actif, vérifié et avoir un téléphone vérifié."}
        )


@transaction.atomic
def activate_subscription(provider_id, actor, *, plan_id, note=""):
    if not can_manage_subscriptions(actor):
        raise PermissionDenied("Gestion des abonnements non autorisée.")

    now = timezone.now()
    provider = _locked_provider(provider_id)
    _validate_provider_for_subscription(provider)
    plan = _locked_plan(plan_id)

    subscription = (
        ProviderSubscription.objects.select_for_update()
        .filter(provider=provider)
        .first()
    )
    if subscription is not None:
        _expire_if_needed(subscription, actor=actor, now=now)
        subscription.refresh_from_db()
        if (
            subscription.status == ProviderSubscription.Status.ACTIVE
            and subscription.ends_at > now
        ):
            raise ValidationError(
                {"detail": "Ce prestataire possède déjà un abonnement actif."}
            )

        subscription.plan = plan
        subscription.status = ProviderSubscription.Status.ACTIVE
        subscription.starts_at = now
        subscription.ends_at = now + timedelta(days=plan.duration_days)
        subscription.activated_by = actor
        subscription.cancelled_at = None
        subscription.save(
            update_fields=[
                "plan",
                "status",
                "starts_at",
                "ends_at",
                "activated_by",
                "cancelled_at",
                "updated_at",
            ]
        )
    else:
        subscription = ProviderSubscription.objects.create(
            provider=provider,
            plan=plan,
            status=ProviderSubscription.Status.ACTIVE,
            starts_at=now,
            ends_at=now + timedelta(days=plan.duration_days),
            activated_by=actor,
        )

    _record_history(
        subscription,
        actor=actor,
        action=SubscriptionHistory.Action.ACTIVATED,
        note=note,
    )
    return subscription


@transaction.atomic
def renew_subscription(subscription_id, actor, *, plan_id=None, note=""):
    if not can_manage_subscriptions(actor):
        raise PermissionDenied("Gestion des abonnements non autorisée.")

    try:
        subscription = (
            ProviderSubscription.objects.select_for_update()
            .select_related("plan", "provider__user")
            .get(pk=subscription_id)
        )
    except ProviderSubscription.DoesNotExist as exc:
        raise NotFound("Abonnement introuvable.") from exc

    _validate_provider_for_subscription(subscription.provider)
    now = timezone.now()
    _expire_if_needed(subscription, actor=actor, now=now)
    subscription.refresh_from_db()

    if subscription.status == ProviderSubscription.Status.CANCELLED:
        raise ValidationError(
            {"detail": "Un abonnement annulé doit être réactivé via l'activation."}
        )

    plan = _locked_plan(plan_id) if plan_id else _locked_plan(subscription.plan_id)

    if (
        subscription.status == ProviderSubscription.Status.ACTIVE
        and subscription.ends_at > now
    ):
        new_starts_at = subscription.starts_at
        base = subscription.ends_at
    else:
        new_starts_at = now
        base = now

    subscription.plan = plan
    subscription.status = ProviderSubscription.Status.ACTIVE
    subscription.starts_at = new_starts_at
    subscription.ends_at = base + timedelta(days=plan.duration_days)
    subscription.activated_by = actor
    subscription.cancelled_at = None
    subscription.save(
        update_fields=[
            "plan",
            "status",
            "starts_at",
            "ends_at",
            "activated_by",
            "cancelled_at",
            "updated_at",
        ]
    )
    _record_history(
        subscription,
        actor=actor,
        action=SubscriptionHistory.Action.RENEWED,
        note=note,
    )
    return subscription


@transaction.atomic
def cancel_subscription(subscription_id, actor, *, note):
    if not can_manage_subscriptions(actor):
        raise PermissionDenied("Gestion des abonnements non autorisée.")

    try:
        subscription = (
            ProviderSubscription.objects.select_for_update()
            .select_related("plan")
            .get(pk=subscription_id)
        )
    except ProviderSubscription.DoesNotExist as exc:
        raise NotFound("Abonnement introuvable.") from exc

    now = timezone.now()
    if _expire_if_needed(subscription, actor=actor, now=now):
        raise ValidationError({"detail": "Cet abonnement est déjà expiré."})

    if subscription.status != ProviderSubscription.Status.ACTIVE:
        raise ValidationError({"detail": "Cet abonnement n'est pas actif."})

    subscription.status = ProviderSubscription.Status.CANCELLED
    subscription.cancelled_at = now
    subscription.save(
        update_fields=["status", "cancelled_at", "updated_at"]
    )
    _record_history(
        subscription,
        actor=actor,
        action=SubscriptionHistory.Action.CANCELLED,
        note=note,
    )
    return subscription



@transaction.atomic
def apply_paid_subscription(
    provider_id,
    *,
    plan_id,
    duration_days,
    payment_reference,
):
    """Apply a server-confirmed paid period without trusting client state."""
    if duration_days < 1:
        raise ValidationError({"duration_days": "La durée payée est invalide."})

    now = timezone.now()
    provider = _locked_provider(provider_id)
    _validate_provider_for_subscription(provider)

    try:
        plan = SubscriptionPlan.objects.select_for_update().get(pk=plan_id)
    except SubscriptionPlan.DoesNotExist as exc:
        raise NotFound("Plan payé introuvable.") from exc

    subscription = (
        ProviderSubscription.objects.select_for_update()
        .filter(provider=provider)
        .first()
    )

    if subscription is not None:
        _expire_if_needed(subscription, actor=None, now=now)
        subscription.refresh_from_db()

    if (
        subscription is not None
        and subscription.status == ProviderSubscription.Status.ACTIVE
        and subscription.ends_at > now
    ):
        starts_at = subscription.starts_at
        base = subscription.ends_at
        action = SubscriptionHistory.Action.RENEWED
    else:
        starts_at = now
        base = now
        action = SubscriptionHistory.Action.ACTIVATED

    ends_at = base + timedelta(days=duration_days)

    if subscription is None:
        subscription = ProviderSubscription.objects.create(
            provider=provider,
            plan=plan,
            status=ProviderSubscription.Status.ACTIVE,
            starts_at=starts_at,
            ends_at=ends_at,
            activated_by=None,
        )
    else:
        subscription.plan = plan
        subscription.status = ProviderSubscription.Status.ACTIVE
        subscription.starts_at = starts_at
        subscription.ends_at = ends_at
        subscription.activated_by = None
        subscription.cancelled_at = None
        subscription.save(
            update_fields=[
                "plan",
                "status",
                "starts_at",
                "ends_at",
                "activated_by",
                "cancelled_at",
                "updated_at",
            ]
        )

    _record_history(
        subscription,
        actor=None,
        action=action,
        note=f"Paiement confirmé {payment_reference}",
    )
    return subscription
