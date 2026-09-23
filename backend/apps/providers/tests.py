from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Category, Trade
from apps.locations.models import City, Commune, Neighborhood

from .models import ProviderProfile, ProviderReview
from .review import review_provider


class ProviderTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(phone="+22312345678", password="Strong-password-2026!")
        self.admin_user = get_user_model().objects.create_superuser(
            phone="+22312345679", password="Strong-admin-2026!"
        )
        city = City.objects.get(name="Bamako")
        commune = Commune.objects.create(city=city, name="Commune exemple")
        self.area = Neighborhood.objects.create(commune=commune, name="Quartier exemple")
        self.category = Category.objects.create(name="Maison")
        self.trade = Trade.objects.create(category=self.category, name="Plomberie")
        self.client = APIClient(enforce_csrf_checks=True)
        self.client.force_login(self.user)
        self.csrf_token = self.client.get("/api/v1/auth/csrf/").json()["csrfToken"]
        self.application = {
            "legal_name": "Nom juridique exemple",
            "display_name": "Atelier exemple",
            "description": "Réparations à domicile",
            "trade_ids": [str(self.trade.pk)],
            "area_ids": [str(self.area.pk)],
        }

    def request(self, method, path, payload, csrf=True):
        headers = {"HTTP_X_CSRFTOKEN": self.csrf_token} if csrf else {}
        return getattr(self.client, method)(path, payload, format="json", **headers)

    def apply(self):
        self.user.phone_verified_at = timezone.now()
        self.user.save(update_fields=["phone_verified_at"])
        self.assertEqual(self.request("post", "/api/v1/providers/application/", self.application).status_code, 201)
        return ProviderProfile.objects.get(user=self.user)

    def test_client_applies_without_gaining_role_or_review_permissions(self):
        path = "/api/v1/providers/application/"
        self.assertEqual(self.request("post", path, self.application, csrf=False).status_code, 403)
        self.assertEqual(self.request("post", path, self.application).status_code, 403)
        self.user.phone_verified_at = timezone.now()
        self.user.save(update_fields=["phone_verified_at"])
        payload = {**self.application, "status": "VERIFIED", "identity_checked": True}
        self.assertEqual(self.request("post", path, payload).status_code, 400)
        self.assertEqual(ProviderProfile.objects.count(), 0)
        response = self.request("post", path, self.application)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "PENDING")
        self.assertNotIn("identity_checked", response.json())
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, self.user.Role.CLIENT)
        self.assertEqual(self.request("post", path, self.application).status_code, 400)
        self.assertEqual(APIClient().get("/api/v1/providers/").json()["count"], 0)
        with self.assertRaises(PermissionDenied):
            review_provider(ProviderProfile.objects.get().pk, self.user, ProviderReview.Decision.APPROVED)

    def test_admin_review_controls_role_and_public_data(self):
        profile = self.apply()
        profile.review_note = "Contrôle d'identité effectué en personne."
        profile.save(update_fields=["review_note"])
        with self.assertRaises(ValidationError):
            review_provider(profile.pk, self.admin_user, ProviderReview.Decision.APPROVED)
        self.assertEqual(ProviderReview.objects.count(), 0)

        profile.identity_checked = True
        profile.save(update_fields=["identity_checked"])
        review_provider(profile.pk, self.admin_user, ProviderReview.Decision.APPROVED)
        profile.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(profile.status, profile.Status.VERIFIED)
        self.assertFalse(profile.is_available)
        self.assertEqual(self.user.role, self.user.Role.PROVIDER)
        public = APIClient().get("/api/v1/providers/").json()["results"][0]
        for private in ("legal_name", "phone", "review_note", "identity_checked", "verified_by"):
            self.assertNotIn(private, public)
        self.assertEqual(self.request("patch", "/api/v1/providers/application/", {"display_name": "Nouveau"}).status_code, 403)
        self.assertEqual(self.request("patch", "/api/v1/providers/availability/", {"is_available": True}).status_code, 200)

        profile.review_note = "Suspension après contrôle manuel."
        profile.save(update_fields=["review_note"])
        review_provider(profile.pk, self.admin_user, ProviderReview.Decision.SUSPENDED)
        profile.refresh_from_db()
        self.user.refresh_from_db()
        self.assertFalse(profile.is_available)
        self.assertEqual(self.user.role, self.user.Role.CLIENT)
        self.assertEqual(APIClient().get("/api/v1/providers/").json()["count"], 0)
        self.assertEqual(self.request("patch", "/api/v1/providers/availability/", {"is_available": True}).status_code, 403)
        self.assertEqual(list(profile.reviews.values_list("decision", flat=True)), ["SUSPENDED", "APPROVED"])

    def test_admin_action_requires_review_note_and_verified_phone(self):
        profile = self.apply()
        profile.identity_checked = True
        profile.review_note = "Contrôle effectué en personne."
        profile.save(update_fields=["identity_checked", "review_note"])
        self.user.phone_verified_at = None
        self.user.save(update_fields=["phone_verified_at"])
        with self.assertRaises(ValidationError):
            review_provider(profile.pk, self.admin_user, ProviderReview.Decision.APPROVED)
        self.user.phone_verified_at = timezone.now()
        self.user.save(update_fields=["phone_verified_at"])
        admin_client = APIClient()
        admin_client.force_login(self.admin_user)
        self.assertEqual(
            admin_client.get(f"/django-admin/providers/providerprofile/{profile.pk}/change/").status_code, 200
        )
        response = admin_client.post(
            "/django-admin/providers/providerprofile/",
            {"action": "approve_selected", "_selected_action": [str(profile.pk)]},
        )
        self.assertEqual(response.status_code, 302)
        profile.refresh_from_db()
        self.assertEqual(profile.status, profile.Status.VERIFIED)
        self.assertEqual(profile.reviews.count(), 1)
        self.assertEqual(
            admin_client.get(f"/django-admin/providers/providerprofile/{profile.pk}/change/").status_code, 200
        )

    def test_inactive_trade_blocks_approval_and_owner_sees_only_own_file(self):
        profile = self.apply()
        profile.identity_checked = True
        profile.review_note = "Contrôle effectué en personne."
        profile.save(update_fields=["identity_checked", "review_note"])
        self.category.is_active = False
        self.category.save(update_fields=["is_active"])
        with self.assertRaises(ValidationError):
            review_provider(profile.pk, self.admin_user, ProviderReview.Decision.APPROVED)
        self.assertEqual(ProviderReview.objects.count(), 0)
        stranger = get_user_model().objects.create_user(phone="+22312345670", password="Strong-password-2026!")
        other_client = APIClient()
        other_client.force_login(stranger)
        self.assertEqual(other_client.get("/api/v1/providers/application/").status_code, 404)

    def test_rejection_resubmission_resets_private_review_state(self):
        profile = self.apply()
        profile.review_note = "Dossier à compléter."
        profile.save(update_fields=["review_note"])
        review_provider(profile.pk, self.admin_user, ProviderReview.Decision.REJECTED)
        response = self.request("patch", "/api/v1/providers/application/", {"display_name": "Atelier corrigé"})
        self.assertEqual(response.status_code, 200)
        profile.refresh_from_db()
        self.assertEqual(profile.status, profile.Status.PENDING)
        self.assertFalse(profile.identity_checked)
        self.assertEqual(profile.review_note, "")
        self.assertEqual(profile.reviews.first().decision, ProviderReview.Decision.REJECTED)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, self.user.Role.CLIENT)

    def test_staff_without_review_permission_cannot_approve(self):
        profile = self.apply()
        profile.identity_checked = True
        profile.review_note = "Contrôle effectué en personne."
        profile.save(update_fields=["identity_checked", "review_note"])
        staff = get_user_model().objects.create_user(
            phone="+22312345671", password="Strong-password-2026!", role="ADMIN", is_staff=True
        )
        with self.assertRaises(PermissionDenied):
            review_provider(profile.pk, staff, ProviderReview.Decision.APPROVED)
        profile.refresh_from_db()
        self.assertEqual(profile.status, profile.Status.PENDING)

    def test_edit_after_identity_check_requires_fresh_review(self):
        profile = self.apply()
        profile.identity_checked = True
        profile.review_note = "Contrôle effectué en personne."
        profile.save(update_fields=["identity_checked", "review_note"])
        response = self.request("patch", "/api/v1/providers/application/", {"legal_name": "Nom corrigé"})
        self.assertEqual(response.status_code, 200)
        profile.refresh_from_db()
        self.assertFalse(profile.identity_checked)
        self.assertEqual(profile.review_note, "")
        with self.assertRaises(ValidationError):
            review_provider(profile.pk, self.admin_user, ProviderReview.Decision.APPROVED)

    def test_admin_edit_after_identity_check_resets_review(self):
        profile = self.apply()
        profile.identity_checked = True
        profile.review_note = "Contrôle effectué en personne."
        profile.save(update_fields=["identity_checked", "review_note"])
        admin_client = APIClient()
        admin_client.force_login(self.admin_user)
        change_url = f"/django-admin/providers/providerprofile/{profile.pk}/change/"
        inline_prefix = admin_client.get(change_url).context["inline_admin_formsets"][0].formset.prefix
        response = admin_client.post(
            change_url,
            {
                "legal_name": "Nom juridique corrigé",
                "display_name": profile.display_name,
                "description": profile.description,
                "trades": [str(self.trade.pk)],
                "service_areas": [str(self.area.pk)],
                "identity_checked": "on",
                "review_note": "Contrôle effectué en personne.",
                "_save": "Enregistrer",
                f"{inline_prefix}-TOTAL_FORMS": "0",
                f"{inline_prefix}-INITIAL_FORMS": "0",
                f"{inline_prefix}-MIN_NUM_FORMS": "0",
                f"{inline_prefix}-MAX_NUM_FORMS": "1000",
            },
        )
        self.assertEqual(response.status_code, 302)
        profile.refresh_from_db()
        self.assertEqual(profile.legal_name, "Nom juridique corrigé")
        self.assertFalse(profile.identity_checked)
        self.assertEqual(profile.review_note, "")
