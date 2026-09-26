from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .models import ProviderProfile, ProviderReview


def can_review_providers(user):
    return bool(
        user.is_authenticated
        and user.is_active
        and user.is_staff
        and (user.is_superuser or (user.role == user.Role.ADMIN and user.has_perm("providers.verify_provider")))
    )


@transaction.atomic
def review_provider(profile_id, reviewer, decision):
    if not can_review_providers(reviewer):
        raise PermissionDenied("Vérification réservée aux administrateurs habilités.")

    profile = ProviderProfile.objects.select_for_update().get(pk=profile_id)
    user = get_user_model().objects.select_for_update().get(pk=profile.user_id)
    note = profile.review_note.strip()
    if not note:
        raise ValidationError("Ajoutez une note de contrôle avant de prendre une décision.")

    now = timezone.now()
    if decision == ProviderReview.Decision.APPROVED:
        if profile.status != ProviderProfile.Status.PENDING or user.role != user.Role.CLIENT or not user.is_active:
            raise ValidationError("Cette candidature ne peut pas être approuvée.")
        if user.phone_verified_at is None or not profile.identity_checked:
            raise ValidationError("Vérifiez le téléphone et confirmez le contrôle d'identité hors ligne.")
        if not profile.trades.filter(is_active=True, category__is_active=True).exists():
            raise ValidationError("Un métier actif est obligatoire.")
        if not profile.service_areas.filter(
            is_active=True, commune__is_active=True, commune__city__is_active=True, commune__city__region__is_active=True
        ).exists():
            raise ValidationError("Un quartier actif est obligatoire.")
        profile.status = ProviderProfile.Status.VERIFIED
        profile.verified_at = now
        profile.verified_by = reviewer
        profile.is_available = False
        user.role = user.Role.PROVIDER
        user.save(update_fields=["role"])
    elif decision == ProviderReview.Decision.REJECTED:
        if profile.status != ProviderProfile.Status.PENDING or user.role != user.Role.CLIENT:
            raise ValidationError("Seule une candidature en attente peut être refusée.")
        profile.status = ProviderProfile.Status.REJECTED
        profile.identity_checked = False
    elif decision == ProviderReview.Decision.SUSPENDED:
        if profile.status != ProviderProfile.Status.VERIFIED or user.role != user.Role.PROVIDER:
            raise ValidationError("Seul un prestataire vérifié peut être suspendu.")
        profile.status = ProviderProfile.Status.SUSPENDED
        profile.is_available = False
        user.role = user.Role.CLIENT
        user.save(update_fields=["role"])
    elif decision == ProviderReview.Decision.REOPENED:
        if profile.status not in (ProviderProfile.Status.REJECTED, ProviderProfile.Status.SUSPENDED):
            raise ValidationError("Seul un dossier refusé ou suspendu peut être rouvert.")
        if user.role != user.Role.CLIENT:
            raise ValidationError("Le rôle du compte doit d'abord être corrigé.")
        profile.status = ProviderProfile.Status.PENDING
        profile.is_available = False
        profile.identity_checked = False
        profile.verified_at = None
        profile.verified_by = None
        profile.review_note = ""
    else:
        raise ValidationError("Décision inconnue.")

    profile.save()
    ProviderReview.objects.create(profile=profile, reviewer=reviewer, decision=decision, note=note)
    return profile
