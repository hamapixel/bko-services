from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.notifications.models import Notification
from apps.notifications.services import create_notification
from apps.requests.models import ServiceRequest

from .models import Review


@transaction.atomic
def create_review(request_id, user, *, rating, comment=""):
    try:
        service_request = (
            ServiceRequest.objects.select_for_update()
            .select_related("client", "assigned_provider")
            .get(pk=request_id)
        )
    except ServiceRequest.DoesNotExist as exc:
        raise NotFound("Demande introuvable.") from exc

    locked_user = get_user_model().objects.select_for_update().get(pk=user.pk)

    if (
        not locked_user.is_active
        or locked_user.role != locked_user.Role.CLIENT
        or service_request.client_id != locked_user.pk
    ):
        raise NotFound("Demande introuvable.")

    if service_request.status != ServiceRequest.Status.CLIENT_CONFIRMED:
        raise ValidationError(
            {"detail": "Un avis est possible uniquement après confirmation de la fin de l'intervention."}
        )

    if service_request.assigned_provider_id is None:
        raise ValidationError({"detail": "Aucun prestataire n'est attribué à cette demande."})

    if Review.objects.filter(service_request=service_request).exists():
        raise ValidationError({"detail": "Un avis existe déjà pour cette intervention."})

    review = Review.objects.create(
        service_request=service_request,
        client=locked_user,
        provider=service_request.assigned_provider,
        rating=rating,
        comment=comment,
    )
    create_notification(
        recipient_id=service_request.assigned_provider.user_id,
        kind=Notification.Kind.REVIEW_RECEIVED,
        title="Nouvel avis reçu",
        message=f"Un client vous a attribué une note de {rating}/5.",
        service_request=service_request,
    )
    return review
