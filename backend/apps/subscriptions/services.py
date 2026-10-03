from datetime import timedelta

from django.db import transaction
from django.db.models import Case, Count, F, IntegerField, Q, When
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.providers.models import ProviderProfile
from apps.requests.models import ServiceRequest

from .models import ProviderSubscription, SubscriptionHistory, SubscriptionPlan


ACTIVE_INTERVENTION_STATUSES = (
    ServiceRequest.Status.ACCEPTED,
    ServiceRequest.Status.EN_ROUTE,
    ServiceRequest.Status.ARRIVED,
    ServiceRequest.Status.IN_PROGRESS,
    ServiceRequest.Status.DISPUTED,
)


def _schedule_waiting_request_retry(provider_id):
    from apps.requests.matching import schedule_waiting_request_retry

    schedule_waiting_request_retry(provider_id)


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


def _period_contains(starts_at, ends_at, at):
    return starts_at is not None and ends_at is not None and starts_at <= at < ends_at


def effective_subscription_period(subscription, at=None):
    at = at or timezone.now()
    if (
        subscription.status == ProviderSubscription.Status.ACTIVE
        and subscription.pending_plan_id
        and subscription.pending_starts_at is not None
        and subscription.pending_ends_at is not None
        and at >= subscription.pending_starts_at
    ):
        return (
            subscription.pending_plan,
            subscription.pending_starts_at,
            subscription.pending_ends_at,
        )
    return subscription.plan, subscription.starts_at, subscription.ends_at


def effective_subscription_status(subscription, at=None):
    at = at or timezone.now()
    if subscription.status != ProviderSubscription.Status.ACTIVE:
        return subscription.status

    if _period_contains(subscription.starts_at, subscription.ends_at, at):
        return ProviderSubscription.Status.ACTIVE
    if (
        subscription.pending_plan_id
        and _period_contains(
            subscription.pending_starts_at,
            subscription.pending_ends_at,
            at,
        )
    ):
        return ProviderSubscription.Status.ACTIVE

    latest_end = subscription.pending_ends_at or subscription.ends_at
    if latest_end <= at:
        return ProviderSubscription.Status.EXPIRED
    return subscription.status


def subscription_is_effective(subscription, *, urgent=False, at=None):
    at = at or timezone.now()
    if subscription.status != ProviderSubscription.Status.ACTIVE:
        return False

    if (
        subscription.pending_plan_id
        and _period_contains(
            subscription.pending_starts_at,
            subscription.pending_ends_at,
            at,
        )
    ):
        plan = subscription.pending_plan
    elif _period_contains(subscription.starts_at, subscription.ends_at, at):
        plan = subscription.plan
    else:
        return False

    if not plan.can_receive_requests:
        return False
    if urgent and not plan.can_receive_urgent_requests:
        return False

    limit = plan.max_active_jobs
    if limit is not None and ServiceRequest.objects.filter(
        assigned_provider_id=subscription.provider_id,
        status__in=ACTIVE_INTERVENTION_STATUSES,
    ).count() >= limit:
        return False
    return True


def provider_has_entitlement(provider_id, *, urgent=False, at=None):
    return eligible_provider_ids_queryset(urgent=urgent, at=at).filter(
        provider_id=provider_id
    ).exists()


def eligible_provider_ids_queryset(*, urgent=False, at=None):
    at = at or timezone.now()

    current_window = Q(
        starts_at__lte=at,
        ends_at__gt=at,
        plan__can_receive_requests=True,
    )
    pending_window = Q(
        pending_plan__isnull=False,
        pending_starts_at__lte=at,
        pending_ends_at__gt=at,
        pending_plan__can_receive_requests=True,
    )
    if urgent:
        current_window &= Q(plan__can_receive_urgent_requests=True)
        pending_window &= Q(pending_plan__can_receive_urgent_requests=True)

    queryset = ProviderSubscription.objects.filter(
        status=ProviderSubscription.Status.ACTIVE,
    ).filter(current_window | pending_window)

    queryset = queryset.annotate(
        active_jobs=Count(
            "provider__assigned_requests",
            filter=Q(provider__assigned_requests__status__in=ACTIVE_INTERVENTION_STATUSES),
            distinct=True,
        ),
        effective_max_active_jobs=Case(
            When(
                pending_plan__isnull=False,
                pending_starts_at__lte=at,
                pending_ends_at__gt=at,
                then=F("pending_plan__max_active_jobs"),
            ),
            default=F("plan__max_active_jobs"),
            output_field=IntegerField(),
        ),
    ).filter(
        Q(effective_max_active_jobs__isnull=True)
        | Q(active_jobs__lt=F("effective_max_active_jobs"))
    )
    return queryset.values("provider_id")


def _record_history(
    subscription,
    *,
    actor,
    action,
    note="",
    plan=None,
    starts_at=None,
    ends_at=None,
):
    history_plan = plan or subscription.plan
    SubscriptionHistory.objects.create(
        subscription=subscription,
        actor=actor,
        action=action,
        plan_code=history_plan.code,
        plan_name=history_plan.name,
        starts_at=starts_at or subscription.starts_at,
        ends_at=ends_at or subscription.ends_at,
        note=note.strip(),
    )


def _materialize_pending_if_due(subscription, *, now):
    if (
        subscription.status != ProviderSubscription.Status.ACTIVE
        or not subscription.pending_plan_id
        or subscription.pending_starts_at is None
        or subscription.pending_ends_at is None
        or subscription.pending_starts_at > now
    ):
        return False

    subscription.plan = subscription.pending_plan
    subscription.starts_at = subscription.pending_starts_at
    subscription.ends_at = subscription.pending_ends_at
    subscription.pending_plan = None
    subscription.pending_starts_at = None
    subscription.pending_ends_at = None
    subscription.save(
        update_fields=[
            "plan",
            "starts_at",
            "ends_at",
            "pending_plan",
            "pending_starts_at",
            "pending_ends_at",
            "updated_at",
        ]
    )
    return True


def _expire_if_needed(subscription, *, actor=None, now=None):
    now = now or timezone.now()
    _materialize_pending_if_due(subscription, now=now)
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


def _apply_plan_period(
    subscription,
    *,
    plan,
    duration_days,
    actor,
    note,
    now,
):
    _expire_if_needed(subscription, actor=actor, now=now)
    subscription.refresh_from_db()

    if (
        subscription.pending_plan_id
        and subscription.pending_starts_at is not None
        and subscription.pending_starts_at > now
    ):
        raise ValidationError(
            {
                "detail": (
                    "Un changement de plan est déjà programmé. "
                    "Attendez son démarrage avant d'en choisir un autre."
                )
            }
        )

    active_now = (
        subscription.status == ProviderSubscription.Status.ACTIVE
        and _period_contains(subscription.starts_at, subscription.ends_at, now)
    )

    if not active_now:
        subscription.plan = plan
        subscription.status = ProviderSubscription.Status.ACTIVE
        subscription.starts_at = now
        subscription.ends_at = now + timedelta(days=duration_days)
        subscription.pending_plan = None
        subscription.pending_starts_at = None
        subscription.pending_ends_at = None
        subscription.activated_by = actor
        subscription.cancelled_at = None
        subscription.save(
            update_fields=[
                "plan",
                "status",
                "starts_at",
                "ends_at",
                "pending_plan",
                "pending_starts_at",
                "pending_ends_at",
                "activated_by",
                "cancelled_at",
                "updated_at",
            ]
        )
        _record_history(
            subscription,
            actor=actor,
            action=SubscriptionHistory.Action.ACTIVATED,
            note=note,
        )
        return subscription

    base = subscription.ends_at
    target_end = base + timedelta(days=duration_days)

    if plan.pk == subscription.plan_id:
        subscription.ends_at = target_end
        subscription.activated_by = actor
        subscription.cancelled_at = None
        subscription.save(
            update_fields=[
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

    immediate_upgrade = (
        subscription.plan.price_xof == 0
        or plan.price_xof > subscription.plan.price_xof
    )
    if immediate_upgrade:
        subscription.plan = plan
        subscription.starts_at = now
        subscription.ends_at = target_end
        subscription.pending_plan = None
        subscription.pending_starts_at = None
        subscription.pending_ends_at = None
        subscription.activated_by = actor
        subscription.cancelled_at = None
        subscription.save(
            update_fields=[
                "plan",
                "starts_at",
                "ends_at",
                "pending_plan",
                "pending_starts_at",
                "pending_ends_at",
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
            plan=plan,
            starts_at=now,
            ends_at=target_end,
        )
        return subscription

    subscription.pending_plan = plan
    subscription.pending_starts_at = base
    subscription.pending_ends_at = target_end
    subscription.save(
        update_fields=[
            "pending_plan",
            "pending_starts_at",
            "pending_ends_at",
            "updated_at",
        ]
    )
    scheduled_note = "Changement de plan programmé à la fin de la période en cours."
    if note.strip():
        scheduled_note += f" {note.strip()}"
    _record_history(
        subscription,
        actor=actor,
        action=SubscriptionHistory.Action.RENEWED,
        note=scheduled_note,
        plan=plan,
        starts_at=base,
        ends_at=target_end,
    )
    return subscription


@transaction.atomic
def activate_subscription(provider_id, actor, *, plan_id, note=""):
    if not can_manage_subscriptions(actor):
        raise PermissionDenied("Gestion des abonnements non autorisée.")

    now = timezone.now()
    provider = _locked_provider(provider_id)
    _validate_provider_for_subscription(provider)
    plan = _locked_plan(plan_id)

    subscription = (
        ProviderSubscription.objects.select_for_update(of=("self",))
        .select_related("plan", "pending_plan")
        .filter(provider=provider)
        .first()
    )
    if plan.price_xof == 0 and subscription is not None and subscription.free_trial_used_at:
        raise ValidationError(
            {"detail": "L'essai gratuit a déjà été utilisé. Choisissez un abonnement payant."}
        )
    if subscription is not None:
        _expire_if_needed(subscription, actor=actor, now=now)
        subscription.refresh_from_db()
        if (
            subscription.status == ProviderSubscription.Status.ACTIVE
            and effective_subscription_status(subscription, at=now)
            == ProviderSubscription.Status.ACTIVE
        ):
            raise ValidationError(
                {"detail": "Ce prestataire possède déjà un abonnement actif."}
            )

        subscription.plan = plan
        subscription.status = ProviderSubscription.Status.ACTIVE
        subscription.starts_at = now
        subscription.ends_at = now + timedelta(days=plan.duration_days)
        subscription.pending_plan = None
        subscription.pending_starts_at = None
        subscription.pending_ends_at = None
        subscription.activated_by = actor
        subscription.cancelled_at = None
        if plan.price_xof == 0:
            subscription.free_trial_used_at = now
        subscription.save(
            update_fields=[
                "plan",
                "status",
                "starts_at",
                "ends_at",
                "pending_plan",
                "pending_starts_at",
                "pending_ends_at",
                "activated_by",
                "cancelled_at",
                "free_trial_used_at",
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
            free_trial_used_at=now if plan.price_xof == 0 else None,
        )

    _record_history(
        subscription,
        actor=actor,
        action=SubscriptionHistory.Action.ACTIVATED,
        note=note,
    )
    _schedule_waiting_request_retry(provider.pk)
    return subscription


@transaction.atomic
def renew_subscription(subscription_id, actor, *, plan_id=None, note=""):
    if not can_manage_subscriptions(actor):
        raise PermissionDenied("Gestion des abonnements non autorisée.")

    try:
        subscription = (
            ProviderSubscription.objects.select_for_update(of=("self",))
            .select_related("plan", "pending_plan", "provider__user")
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
    if plan.price_xof == 0:
        raise ValidationError(
            {"detail": "L'essai gratuit ne peut pas être renouvelé. Choisissez un abonnement payant."}
        )

    _apply_plan_period(
        subscription,
        plan=plan,
        duration_days=plan.duration_days,
        actor=actor,
        note=note,
        now=now,
    )
    _schedule_waiting_request_retry(subscription.provider_id)
    return subscription


@transaction.atomic
def cancel_subscription(subscription_id, actor, *, note):
    if not can_manage_subscriptions(actor):
        raise PermissionDenied("Gestion des abonnements non autorisée.")

    try:
        subscription = (
            ProviderSubscription.objects.select_for_update(of=("self",))
            .select_related("plan", "pending_plan")
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
    subscription.pending_plan = None
    subscription.pending_starts_at = None
    subscription.pending_ends_at = None
    subscription.save(
        update_fields=[
            "status",
            "cancelled_at",
            "pending_plan",
            "pending_starts_at",
            "pending_ends_at",
            "updated_at",
        ]
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
        ProviderSubscription.objects.select_for_update(of=("self",))
        .select_related("plan", "pending_plan")
        .filter(provider=provider)
        .first()
    )

    if subscription is None:
        subscription = ProviderSubscription.objects.create(
            provider=provider,
            plan=plan,
            status=ProviderSubscription.Status.ACTIVE,
            starts_at=now,
            ends_at=now + timedelta(days=duration_days),
            activated_by=None,
        )
        _record_history(
            subscription,
            actor=None,
            action=SubscriptionHistory.Action.ACTIVATED,
            note=f"Paiement confirmé {payment_reference}",
        )
    else:
        _apply_plan_period(
            subscription,
            plan=plan,
            duration_days=duration_days,
            actor=None,
            note=f"Paiement confirmé {payment_reference}",
            now=now,
        )

    _schedule_waiting_request_retry(provider.pk)
    return subscription
