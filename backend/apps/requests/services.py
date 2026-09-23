from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import RequestStatusHistory, ServiceRequest


@transaction.atomic
def create_service_request(user_id, *, trade, neighborhood, title, description, address_detail, priority):
    user = get_user_model().objects.select_for_update().get(pk=user_id)
    if not user.is_active or user.role != user.Role.CLIENT or user.phone_verified_at is None:
        raise PermissionDenied("Un compte client avec téléphone vérifié est nécessaire.")
    if not trade.is_active or not trade.category.is_active:
        raise ValidationError({"trade": "Ce métier n'est plus disponible."})
    if not neighborhood.is_active or not neighborhood.commune.is_active or not neighborhood.commune.city.is_active:
        raise ValidationError({"neighborhood": "Ce quartier n'est plus disponible."})

    service_request = ServiceRequest.objects.create(
        client=user,
        trade=trade,
        neighborhood=neighborhood,
        title=title,
        description=description,
        address_detail=address_detail,
        priority=priority,
    )
    RequestStatusHistory.objects.create(
        service_request=service_request,
        actor=user,
        previous_status="",
        new_status=ServiceRequest.Status.CREATED,
    )
    return service_request
