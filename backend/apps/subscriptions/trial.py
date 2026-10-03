from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.providers.models import ProviderProfile

from .models import ProviderSubscription, SubscriptionHistory, SubscriptionPlan


TRIAL_PLAN_CODE = "essai-14j"


@transaction.atomic
def activate_own_free_trial(user):
    """Activate the one-time free trial for a newly approved provider.

    This flow is intentionally provider-self-service, but all eligibility checks
    remain server-side. The trial is only available before any subscription has
    ever been created for the provider.
    """
    if (
        not user.is_authenticated
        or not user.is_active
        or user.role != user.Role.PROVIDER
        or user.phone_verified_at is None
    ):
        raise PermissionDenied(
            "Un prestataire actif avec téléphone vérifié est nécessaire."
        )

    try:
        provider = (
            ProviderProfile.objects.select_for_update()
            .select_related("user")
            .get(user=user, status=ProviderProfile.Status.VERIFIED)
        )
    except ProviderProfile.DoesNotExist as exc:
        raise PermissionDenied("Un prestataire vérifié est nécessaire.") from exc

    existing = (
        ProviderSubscription.objects.select_for_update()
        .filter(provider=provider)
        .first()
    )
    if existing is not None:
        if existing.free_trial_used_at is not None:
            raise ValidationError(
                {"detail": "Votre essai gratuit de 14 jours a déjà été utilisé."}
            )
        raise ValidationError(
            {
                "detail": (
                    "L'essai gratuit est réservé au démarrage, avant le premier "
                    "abonnement payant."
                )
            }
        )

    try:
        plan = SubscriptionPlan.objects.select_for_update().get(
            code=TRIAL_PLAN_CODE,
            is_active=True,
            price_xof=0,
        )
    except SubscriptionPlan.DoesNotExist as exc:
        raise NotFound("L'essai gratuit n'est pas disponible.") from exc

    now = timezone.now()
    subscription = ProviderSubscription.objects.create(
        provider=provider,
        plan=plan,
        status=ProviderSubscription.Status.ACTIVE,
        starts_at=now,
        ends_at=now + timedelta(days=plan.duration_days),
        activated_by=None,
        free_trial_used_at=now,
    )
    SubscriptionHistory.objects.create(
        subscription=subscription,
        actor=user,
        action=SubscriptionHistory.Action.ACTIVATED,
        plan_code=plan.code,
        plan_name=plan.name,
        starts_at=subscription.starts_at,
        ends_at=subscription.ends_at,
        note="Essai gratuit activé par le prestataire après validation du profil.",
    )

    def retry_waiting_requests():
        from apps.requests.matching import schedule_waiting_request_retry

        schedule_waiting_request_retry(provider.pk)

    transaction.on_commit(retry_waiting_requests)
    return subscription
