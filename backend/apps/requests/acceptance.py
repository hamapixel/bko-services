from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.notifications.models import Notification
from apps.notifications.services import create_notification
from apps.providers.models import ProviderProfile
from apps.subscriptions.services import provider_has_entitlement

from .models import RequestStatusHistory, ServiceOffer, ServiceRequest


def _offer_request_id_for_user(offer_id, user):
    if not user.is_authenticated:
        raise NotFound("Offre introuvable.")

    request_id = (
        ServiceOffer.objects.filter(pk=offer_id, provider__user_id=user.pk)
        .values_list("service_request_id", flat=True)
        .first()
    )
    if request_id is None:
        raise NotFound("Offre introuvable.")
    return request_id


def _validate_provider_eligibility(provider, user, service_request):
    if (
        not user.is_active
        or user.role != user.Role.PROVIDER
        or user.phone_verified_at is None
        or provider.status != ProviderProfile.Status.VERIFIED
        or not provider.is_available
    ):
        raise ValidationError({"offer": "Votre compte prestataire n'est plus éligible à cette demande."})

    trade = service_request.trade
    neighborhood = service_request.neighborhood

    if not trade.is_active or not trade.category.is_active:
        raise ValidationError({"offer": "Le métier de cette demande n'est plus disponible."})

    if (
        not neighborhood.is_active
        or not neighborhood.commune.is_active
        or not neighborhood.commune.city.is_active
    ):
        raise ValidationError({"offer": "Le quartier de cette demande n'est plus disponible."})

    if not provider.trades.filter(pk=trade.pk).exists():
        raise ValidationError({"offer": "Vous n'êtes plus rattaché au métier demandé."})

    if not provider.service_areas.filter(pk=neighborhood.pk).exists():
        raise ValidationError({"offer": "Vous ne desservez plus le quartier demandé."})

    is_urgent = service_request.priority == ServiceRequest.Priority.URGENT
    if not provider_has_entitlement(provider.pk, urgent=is_urgent):
        raise ValidationError(
            {"offer": "Votre abonnement ne permet plus d'accepter cette demande."}
        )


@transaction.atomic
def accept_offer(offer_id, user):
    request_id = _offer_request_id_for_user(offer_id, user)

    service_request = (
        ServiceRequest.objects.select_for_update()
        .select_related(
            "trade__category",
            "neighborhood__commune__city",
        )
        .get(pk=request_id)
    )

    offer = (
        ServiceOffer.objects.select_for_update()
        .select_related("provider")
        .get(pk=offer_id, service_request=service_request)
    )

    provider = ProviderProfile.objects.select_for_update().get(pk=offer.provider_id)
    locked_user = get_user_model().objects.select_for_update().get(pk=user.pk)

    if provider.user_id != locked_user.pk:
        raise NotFound("Offre introuvable.")

    if service_request.status != ServiceRequest.Status.OFFERED or service_request.assigned_provider_id is not None:
        raise ValidationError({"offer": "Cette demande a déjà été attribuée ou n'est plus disponible."})

    if offer.status != ServiceOffer.Status.PENDING:
        raise ValidationError({"offer": "Cette offre n'est plus en attente."})

    _validate_provider_eligibility(provider, locked_user, service_request)

    service_request.assigned_provider = provider
    service_request.status = ServiceRequest.Status.ACCEPTED
    service_request.save(update_fields=["assigned_provider", "status", "updated_at"])

    offer.status = ServiceOffer.Status.ACCEPTED
    offer.save(update_fields=["status", "updated_at"])

    cancelled_provider_user_ids = list(
        ServiceOffer.objects.filter(
            service_request=service_request,
            status=ServiceOffer.Status.PENDING,
        )
        .exclude(pk=offer.pk)
        .values_list("provider__user_id", flat=True)
    )

    ServiceOffer.objects.filter(
        service_request=service_request,
        status=ServiceOffer.Status.PENDING,
    ).exclude(pk=offer.pk).update(
        status=ServiceOffer.Status.CANCELLED,
        updated_at=timezone.now(),
    )

    RequestStatusHistory.objects.create(
        service_request=service_request,
        actor=locked_user,
        previous_status=ServiceRequest.Status.OFFERED,
        new_status=ServiceRequest.Status.ACCEPTED,
    )

    create_notification(
        recipient_id=service_request.client_id,
        kind=Notification.Kind.REQUEST_ACCEPTED,
        title="Prestataire attribué",
        message="Un prestataire a accepté votre demande. Vous pouvez maintenant suivre l'intervention.",
        service_request=service_request,
    )
    for provider_user_id in cancelled_provider_user_ids:
        create_notification(
            recipient_id=provider_user_id,
            kind=Notification.Kind.OFFER_CANCELLED,
            title="Demande déjà attribuée",
            message="Cette demande a été acceptée par un autre prestataire et n'est plus disponible.",
            service_request=service_request,
        )

    return offer, service_request
