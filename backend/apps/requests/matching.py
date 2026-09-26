from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.notifications.models import Notification
from apps.notifications.services import create_notification
from apps.providers.models import ProviderProfile
from apps.subscriptions.services import eligible_provider_ids_queryset

from .models import RequestStatusHistory, ServiceOffer, ServiceRequest


def can_dispatch_requests(user):
    return bool(
        user.is_authenticated
        and user.is_active
        and user.is_staff
        and (user.is_superuser or (user.role == user.Role.ADMIN and user.has_perm("requests.dispatch_request")))
    )


@transaction.atomic
def dispatch_request(request_id, actor):
    if not can_dispatch_requests(actor):
        raise PermissionDenied("Recherche réservée aux administrateurs habilités.")
    return _match_request(request_id, actor)


@transaction.atomic
def dispatch_new_request(request_id, client):
    """Find eligible providers immediately after a verified client creates a request."""
    return _match_request(request_id, client)


def _match_request(request_id, actor):
    service_request = ServiceRequest.objects.select_for_update().get(pk=request_id)
    if service_request.status not in (ServiceRequest.Status.CREATED, ServiceRequest.Status.SEARCHING):
        raise ValidationError("Cette demande n'est pas en attente de recherche.")
    if service_request.offers.exists():
        raise ValidationError("Des offres existent déjà pour cette demande.")
    trade = service_request.trade
    neighborhood = service_request.neighborhood
    if not trade.is_active or not trade.category.is_active:
        raise ValidationError("Le métier de la demande est désactivé.")
    if (not neighborhood.is_active or not neighborhood.commune.is_active
            or not neighborhood.commune.city.is_active
            or not neighborhood.commune.city.region or not neighborhood.commune.city.region.is_active):
        raise ValidationError("Le quartier de la demande est désactivé.")

    if service_request.status == ServiceRequest.Status.CREATED:
        service_request.status = ServiceRequest.Status.SEARCHING
        service_request.save(update_fields=["status", "updated_at"])
        RequestStatusHistory.objects.create(
            service_request=service_request,
            actor=actor,
            previous_status=ServiceRequest.Status.CREATED,
            new_status=ServiceRequest.Status.SEARCHING,
        )

    is_urgent = service_request.priority == ServiceRequest.Priority.URGENT
    limit = 5 if is_urgent else 1
    entitled_provider_ids = eligible_provider_ids_queryset(urgent=is_urgent)
    candidates = ProviderProfile.objects.select_related("user").filter(
        pk__in=entitled_provider_ids,
        status=ProviderProfile.Status.VERIFIED,
        is_available=True,
        user__is_active=True,
        user__role="PROVIDER",
        user__phone_verified_at__isnull=False,
        trades=trade,
        service_areas=neighborhood,
    ).order_by("verified_at", "id")[:limit]

    selected = list(candidates)
    for profile in selected:
        ServiceOffer.objects.create(service_request=service_request, provider=profile)
        create_notification(
            recipient_id=profile.user_id,
            kind=Notification.Kind.OFFER_RECEIVED,
            title="Nouvelle demande disponible",
            message="Une demande compatible avec votre métier et votre zone vous a été proposée.",
            service_request=service_request,
        )

    if selected:
        service_request.status = ServiceRequest.Status.OFFERED
        service_request.save(update_fields=["status", "updated_at"])
        RequestStatusHistory.objects.create(
            service_request=service_request,
            actor=actor,
            previous_status=ServiceRequest.Status.SEARCHING,
            new_status=ServiceRequest.Status.OFFERED,
        )
    return len(selected)
