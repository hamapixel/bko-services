from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.exceptions import NotFound, ValidationError

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


def _locked_request(request_id):
    try:
        return (
            ServiceRequest.objects.select_for_update()
            .select_related("client", "assigned_provider__user")
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
    return service_request
