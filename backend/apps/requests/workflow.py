from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.exceptions import NotFound, ValidationError

from apps.notifications.models import Notification
from apps.notifications.services import create_notification

from .models import RequestStatusHistory, ServiceRequest


PROVIDER_TRANSITIONS = {
    ServiceRequest.Status.ACCEPTED: ServiceRequest.Status.EN_ROUTE,
    ServiceRequest.Status.EN_ROUTE: ServiceRequest.Status.ARRIVED,
    ServiceRequest.Status.ARRIVED: ServiceRequest.Status.IN_PROGRESS,
    ServiceRequest.Status.IN_PROGRESS: ServiceRequest.Status.PROVIDER_COMPLETED,
}

CLIENT_TRANSITIONS = {
    ServiceRequest.Status.PROVIDER_COMPLETED: ServiceRequest.Status.CLIENT_CONFIRMED,
}

CLIENT_NOTIFICATION_BY_STATUS = {
    ServiceRequest.Status.EN_ROUTE: (
        Notification.Kind.PROVIDER_EN_ROUTE,
        "Prestataire en route",
        "Le prestataire est en route pour votre intervention.",
    ),
    ServiceRequest.Status.ARRIVED: (
        Notification.Kind.PROVIDER_ARRIVED,
        "Prestataire arrivé",
        "Le prestataire a indiqué être arrivé sur le lieu de l'intervention.",
    ),
    ServiceRequest.Status.IN_PROGRESS: (
        Notification.Kind.WORK_STARTED,
        "Intervention commencée",
        "Le prestataire a commencé l'intervention.",
    ),
    ServiceRequest.Status.PROVIDER_COMPLETED: (
        Notification.Kind.PROVIDER_COMPLETED,
        "Intervention terminée",
        "Le prestataire a marqué l'intervention comme terminée. Confirmez la fin si tout est correct.",
    ),
}


def _locked_request(request_id):
    try:
        return (
            ServiceRequest.objects.select_for_update()
            .select_related("client")
            .get(pk=request_id)
        )
    except ServiceRequest.DoesNotExist as exc:
        raise NotFound("Intervention introuvable.") from exc


def _provider_owns_request(service_request, user):
    return bool(
        user.is_authenticated
        and user.is_active
        and user.role == user.Role.PROVIDER
        and service_request.assigned_provider_id is not None
        and service_request.assigned_provider.user_id == user.pk
    )


def _client_owns_request(service_request, user):
    return bool(
        user.is_authenticated
        and user.is_active
        and user.role == user.Role.CLIENT
        and service_request.client_id == user.pk
    )


@transaction.atomic
def transition_provider_intervention(request_id, user, target_status):
    service_request = _locked_request(request_id)

    if not _provider_owns_request(service_request, user):
        raise NotFound("Intervention introuvable.")

    expected = PROVIDER_TRANSITIONS.get(service_request.status)
    if expected is None:
        raise ValidationError({"status": "Cette intervention ne peut pas être avancée par le prestataire."})
    if target_status != expected:
        raise ValidationError(
            {
                "status": (
                    f"Transition invalide : l'état attendu après {service_request.status} "
                    f"est {expected}."
                )
            }
        )

    actor = get_user_model().objects.select_for_update().get(pk=user.pk)
    previous_status = service_request.status
    service_request.status = target_status
    service_request.save(update_fields=["status", "updated_at"])
    RequestStatusHistory.objects.create(
        service_request=service_request,
        actor=actor,
        previous_status=previous_status,
        new_status=target_status,
    )

    kind, title, message = CLIENT_NOTIFICATION_BY_STATUS[target_status]
    create_notification(
        recipient_id=service_request.client_id,
        kind=kind,
        title=title,
        message=message,
        service_request=service_request,
    )
    return service_request


@transaction.atomic
def confirm_client_completion(request_id, user):
    service_request = _locked_request(request_id)

    if not _client_owns_request(service_request, user):
        raise NotFound("Demande introuvable.")

    expected = CLIENT_TRANSITIONS.get(service_request.status)
    if expected != ServiceRequest.Status.CLIENT_CONFIRMED:
        raise ValidationError({"status": "Cette demande n'est pas prête à être confirmée."})

    actor = get_user_model().objects.select_for_update().get(pk=user.pk)
    previous_status = service_request.status
    service_request.status = ServiceRequest.Status.CLIENT_CONFIRMED
    service_request.save(update_fields=["status", "updated_at"])
    RequestStatusHistory.objects.create(
        service_request=service_request,
        actor=actor,
        previous_status=previous_status,
        new_status=ServiceRequest.Status.CLIENT_CONFIRMED,
    )
    create_notification(
        recipient_id=service_request.assigned_provider.user_id,
        kind=Notification.Kind.CLIENT_CONFIRMED,
        title="Intervention confirmée",
        message="Le client a confirmé la fin de l'intervention.",
        service_request=service_request,
    )
    return service_request
