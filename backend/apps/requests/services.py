from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.locations.models import City, Neighborhood
from apps.notifications.models import Notification
from apps.notifications.services import create_notification

from .matching import can_dispatch_requests, dispatch_new_request, dispatch_request
from .models import RequestStatusHistory, ServiceRequest


@transaction.atomic
def create_service_request(user_id, *, trade, neighborhood=None, requested_region=None,
                           requested_city="", requested_commune="", requested_neighborhood="",
                           title, description, address_detail, priority):
    user = get_user_model().objects.select_for_update().get(pk=user_id)
    if not user.is_active or user.role != user.Role.CLIENT or user.phone_verified_at is None:
        raise PermissionDenied("Un compte client avec téléphone vérifié est nécessaire.")
    if not trade.is_active or not trade.category.is_active:
        raise ValidationError({"trade": "Ce métier n'est plus disponible."})
    if neighborhood and (not neighborhood.is_active or not neighborhood.commune.is_active
            or not neighborhood.commune.city.is_active
            or not neighborhood.commune.city.region or not neighborhood.commune.city.region.is_active):
        raise ValidationError({"neighborhood": "Ce quartier n'est plus disponible."})
    if not neighborhood and (not requested_region or not requested_region.is_active
                             or not all((requested_city, requested_commune, requested_neighborhood))):
        raise ValidationError({"requested_region": "La zone saisie est incomplète ou indisponible."})
    if not neighborhood and City.objects.filter(
            region=requested_region, is_active=True, communes__is_active=True,
            communes__neighborhoods__is_active=True).exists():
        raise ValidationError({"requested_region": "Choisissez un quartier déjà disponible dans cette région."})

    service_request = ServiceRequest.objects.create(
        client=user,
        trade=trade,
        neighborhood=neighborhood,
        requested_region=requested_region,
        requested_city=requested_city,
        requested_commune=requested_commune,
        requested_neighborhood=requested_neighborhood,
        title=title,
        description=description,
        address_detail=address_detail,
        priority=priority,
        status=ServiceRequest.Status.CREATED if neighborhood else ServiceRequest.Status.LOCATION_PENDING,
    )
    RequestStatusHistory.objects.create(
        service_request=service_request,
        actor=user,
        previous_status="",
        new_status=service_request.status,
    )
    if neighborhood:
        dispatch_new_request(service_request.pk, user)
    else:
        admins = get_user_model().objects.filter(is_active=True, is_staff=True).filter(
            Q(is_superuser=True) | Q(role="ADMIN")
        )
        for admin in admins:
            if admin.is_superuser or admin.has_perm("requests.view_servicerequest"):
                create_notification(
                    recipient_id=admin.pk, kind=Notification.Kind.REQUEST_LOCATION_PENDING,
                    title="Zone de demande à vérifier",
                    message="Un client a indiqué une ville, une commune et un quartier absents du catalogue.",
                    service_request=service_request,
                )
    service_request.refresh_from_db()
    return service_request


@transaction.atomic
def resolve_request_location(request_id, actor, neighborhood):
    if not can_dispatch_requests(actor):
        raise DjangoPermissionDenied("Validation de zone réservée aux administrateurs habilités.")
    service_request = ServiceRequest.objects.select_for_update().get(pk=request_id)
    if service_request.status != ServiceRequest.Status.LOCATION_PENDING or service_request.neighborhood_id:
        raise ValidationError("La zone de cette demande n'est plus à vérifier.")
    area = Neighborhood.objects.select_related("commune__city__region").get(pk=neighborhood.pk)
    if (not area.is_active or not area.commune.is_active or not area.commune.city.is_active
            or not area.commune.city.region or not area.commune.city.region.is_active
            or area.commune.city.region_id != service_request.requested_region_id):
        raise ValidationError("Choisissez un quartier actif de la région demandée par le client.")
    service_request.neighborhood = area
    service_request.status = ServiceRequest.Status.SEARCHING
    service_request.save(update_fields=["neighborhood", "status", "updated_at"])
    RequestStatusHistory.objects.create(
        service_request=service_request, actor=actor,
        previous_status=ServiceRequest.Status.LOCATION_PENDING,
        new_status=ServiceRequest.Status.SEARCHING,
    )
    Notification.objects.filter(
        service_request=service_request, kind=Notification.Kind.REQUEST_LOCATION_PENDING,
        read_at__isnull=True,
    ).update(read_at=timezone.now())
    dispatch_request(service_request.pk, actor)
    return service_request
