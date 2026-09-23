from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.requests.models import RequestStatusHistory, ServiceRequest

from .models import Complaint, ComplaintStatusHistory


DISPUTE_ELIGIBLE_STATUSES = {
    ServiceRequest.Status.ACCEPTED,
    ServiceRequest.Status.EN_ROUTE,
    ServiceRequest.Status.ARRIVED,
    ServiceRequest.Status.IN_PROGRESS,
    ServiceRequest.Status.PROVIDER_COMPLETED,
    ServiceRequest.Status.CLIENT_CONFIRMED,
}

ADMIN_TRANSITIONS = {
    Complaint.Status.OPEN: {
        Complaint.Status.UNDER_REVIEW,
        Complaint.Status.RESOLVED,
        Complaint.Status.REJECTED,
    },
    Complaint.Status.UNDER_REVIEW: {
        Complaint.Status.RESOLVED,
        Complaint.Status.REJECTED,
    },
}


def _is_participant(service_request, user):
    if not user.is_authenticated or not user.is_active:
        return False
    if user.role == user.Role.CLIENT:
        return service_request.client_id == user.pk
    if user.role == user.Role.PROVIDER:
        return bool(
            service_request.assigned_provider_id
            and service_request.assigned_provider.user_id == user.pk
        )
    return False


def _is_admin(user):
    return bool(
        user.is_authenticated
        and user.is_active
        and user.role in {user.Role.ADMIN, user.Role.SUPERADMIN}
    )


@transaction.atomic
def create_complaint(user, *, service_request_id, category, description):
    try:
        service_request = (
            ServiceRequest.objects.select_for_update()
            .select_related("assigned_provider__user")
            .get(pk=service_request_id)
        )
    except ServiceRequest.DoesNotExist as exc:
        raise NotFound("Intervention introuvable.") from exc

    if not _is_participant(service_request, user):
        raise NotFound("Intervention introuvable.")

    if service_request.assigned_provider_id is None:
        raise ValidationError({"service_request_id": "Aucun prestataire n'est attribué à cette demande."})

    if Complaint.objects.filter(
        service_request=service_request,
        status__in=[Complaint.Status.OPEN, Complaint.Status.UNDER_REVIEW],
    ).exists():
        raise ValidationError({"detail": "Une plainte est déjà en cours pour cette intervention."})

    if service_request.status not in DISPUTE_ELIGIBLE_STATUSES:
        raise ValidationError(
            {"service_request_id": "Cette intervention ne peut pas être contestée dans son état actuel."}
        )

    reporter = get_user_model().objects.select_for_update().get(pk=user.pk)
    previous_request_status = service_request.status

    complaint = Complaint.objects.create(
        service_request=service_request,
        reporter=reporter,
        category=category,
        description=description,
        previous_request_status=previous_request_status,
    )
    ComplaintStatusHistory.objects.create(
        complaint=complaint,
        actor=reporter,
        previous_status="",
        new_status=Complaint.Status.OPEN,
    )

    service_request.status = ServiceRequest.Status.DISPUTED
    service_request.save(update_fields=["status", "updated_at"])
    RequestStatusHistory.objects.create(
        service_request=service_request,
        actor=reporter,
        previous_status=previous_request_status,
        new_status=ServiceRequest.Status.DISPUTED,
    )
    return complaint


@transaction.atomic
def transition_complaint(complaint_id, actor, *, target_status, note=""):
    if not _is_admin(actor):
        raise NotFound("Plainte introuvable.")

    try:
        complaint = (
            Complaint.objects.select_for_update()
            .select_related("service_request")
            .get(pk=complaint_id)
        )
    except Complaint.DoesNotExist as exc:
        raise NotFound("Plainte introuvable.") from exc

    allowed = ADMIN_TRANSITIONS.get(complaint.status, set())
    if target_status not in allowed:
        raise ValidationError({"status": "Transition de plainte invalide."})

    is_final = target_status in {
        Complaint.Status.RESOLVED,
        Complaint.Status.REJECTED,
    }
    clean_note = note.strip()
    if is_final and not clean_note:
        raise ValidationError({"note": "Une note de décision est obligatoire."})

    admin_actor = get_user_model().objects.select_for_update().get(pk=actor.pk)
    previous_status = complaint.status
    complaint.status = target_status
    if is_final:
        complaint.resolution_note = clean_note
        complaint.resolved_at = timezone.now()
    complaint.save(
        update_fields=[
            "status",
            "resolution_note",
            "resolved_at",
            "updated_at",
        ]
    )
    ComplaintStatusHistory.objects.create(
        complaint=complaint,
        actor=admin_actor,
        previous_status=previous_status,
        new_status=target_status,
        note=clean_note,
    )

    if is_final:
        service_request = ServiceRequest.objects.select_for_update().get(
            pk=complaint.service_request_id
        )
        if service_request.status != ServiceRequest.Status.DISPUTED:
            raise ValidationError(
                {"service_request": "L'intervention n'est plus dans l'état contesté attendu."}
            )
        restored_status = complaint.previous_request_status
        service_request.status = restored_status
        service_request.save(update_fields=["status", "updated_at"])
        RequestStatusHistory.objects.create(
            service_request=service_request,
            actor=admin_actor,
            previous_status=ServiceRequest.Status.DISPUTED,
            new_status=restored_status,
        )

    return complaint
