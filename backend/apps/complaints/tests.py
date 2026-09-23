from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Category, Trade
from apps.locations.models import City, Commune, Neighborhood
from apps.providers.models import ProviderProfile
from apps.requests.models import RequestStatusHistory, ServiceRequest

from .models import Complaint, ComplaintStatusHistory


class ComplaintTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.client_user = User.objects.create_user(
            phone="+22372000000",
            password="Strong-password-2026!",
            phone_verified_at=timezone.now(),
        )
        self.other_client = User.objects.create_user(
            phone="+22372000001",
            password="Strong-password-2026!",
            phone_verified_at=timezone.now(),
        )
        self.admin_user = User.objects.create_user(
            phone="+22372000002",
            password="Strong-admin-2026!",
            role=User.Role.ADMIN,
            is_staff=True,
            phone_verified_at=timezone.now(),
        )

        city = City.objects.get(name="Bamako")
        commune = Commune.objects.create(city=city, name="Commune plaintes")
        self.area = Neighborhood.objects.create(
            commune=commune,
            name="Quartier plaintes",
        )
        self.trade = Trade.objects.create(
            category=Category.objects.create(name="Catégorie plaintes"),
            name="Métier plaintes",
        )

        self.provider = self.create_provider(
            "+22372000010",
            "Prestataire plainte",
        )
        self.other_provider = self.create_provider(
            "+22372000011",
            "Prestataire étranger",
        )
        self.service_request = self.create_assigned_request(
            status=ServiceRequest.Status.IN_PROGRESS,
        )

    def create_provider(self, phone, display_name):
        User = get_user_model()
        user = User.objects.create_user(
            phone=phone,
            password="Strong-password-2026!",
            role=User.Role.PROVIDER,
            phone_verified_at=timezone.now(),
        )
        profile = ProviderProfile.objects.create(
            user=user,
            legal_name=display_name,
            display_name=display_name,
            status=ProviderProfile.Status.VERIFIED,
            is_available=True,
            verified_at=timezone.now(),
        )
        profile.trades.add(self.trade)
        profile.service_areas.add(self.area)
        return profile

    def create_assigned_request(self, *, status, client=None, provider=None):
        return ServiceRequest.objects.create(
            client=client or self.client_user,
            trade=self.trade,
            neighborhood=self.area,
            assigned_provider=provider or self.provider,
            title="Intervention avec plainte",
            description="Une intervention attribuée.",
            address_detail="Adresse privée",
            status=status,
        )

    def post_complaint(self, user, service_request=None, **extra):
        api = APIClient()
        api.force_login(user)
        payload = {
            "service_request_id": str(
                (service_request or self.service_request).pk
            ),
            "category": Complaint.Category.SERVICE_QUALITY,
            "description": "Le service doit être examiné par l'administration.",
        }
        payload.update(extra)
        return api.post("/api/v1/complaints/", payload, format="json")

    def test_client_can_open_complaint_and_request_becomes_disputed(self):
        response = self.post_complaint(self.client_user)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], Complaint.Status.OPEN)
        self.assertNotIn("reporter", response.json())

        complaint = Complaint.objects.get()
        self.assertEqual(complaint.reporter, self.client_user)
        self.assertEqual(
            complaint.previous_request_status,
            ServiceRequest.Status.IN_PROGRESS,
        )

        self.service_request.refresh_from_db()
        self.assertEqual(
            self.service_request.status,
            ServiceRequest.Status.DISPUTED,
        )
        self.assertTrue(
            RequestStatusHistory.objects.filter(
                service_request=self.service_request,
                actor=self.client_user,
                previous_status=ServiceRequest.Status.IN_PROGRESS,
                new_status=ServiceRequest.Status.DISPUTED,
            ).exists()
        )
        self.assertTrue(
            ComplaintStatusHistory.objects.filter(
                complaint=complaint,
                actor=self.client_user,
                previous_status="",
                new_status=Complaint.Status.OPEN,
            ).exists()
        )

    def test_assigned_provider_can_open_complaint_but_foreign_users_cannot(self):
        own_request = self.create_assigned_request(
            status=ServiceRequest.Status.ACCEPTED,
        )
        provider_response = self.post_complaint(
            self.provider.user,
            own_request,
            category=Complaint.Category.BEHAVIOR,
        )
        self.assertEqual(provider_response.status_code, 201)

        foreign_request = self.create_assigned_request(
            status=ServiceRequest.Status.ACCEPTED,
        )
        self.assertEqual(
            self.post_complaint(
                self.other_provider.user,
                foreign_request,
            ).status_code,
            404,
        )
        self.assertEqual(
            self.post_complaint(
                self.other_client,
                foreign_request,
            ).status_code,
            404,
        )

    def test_complaint_requires_assigned_eligible_intervention(self):
        unassigned = ServiceRequest.objects.create(
            client=self.client_user,
            trade=self.trade,
            neighborhood=self.area,
            title="Non attribuée",
            description="Pas encore attribuée.",
            address_detail="Adresse",
            status=ServiceRequest.Status.CREATED,
        )
        self.assertEqual(
            self.post_complaint(self.client_user, unassigned).status_code,
            400,
        )

        cancelled = self.create_assigned_request(
            status=ServiceRequest.Status.CANCELLED,
        )
        self.assertEqual(
            self.post_complaint(self.client_user, cancelled).status_code,
            400,
        )

    def test_only_one_active_complaint_is_allowed_per_intervention(self):
        self.assertEqual(
            self.post_complaint(self.client_user).status_code,
            201,
        )
        second = self.post_complaint(self.provider.user)
        self.assertEqual(second.status_code, 400)
        self.assertEqual(Complaint.objects.count(), 1)

    def test_database_enforces_one_active_complaint_per_intervention(self):
        Complaint.objects.create(
            service_request=self.service_request,
            reporter=self.client_user,
            category=Complaint.Category.OTHER,
            description="Première plainte",
            previous_request_status=ServiceRequest.Status.IN_PROGRESS,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Complaint.objects.create(
                    service_request=self.service_request,
                    reporter=self.provider.user,
                    category=Complaint.Category.BEHAVIOR,
                    description="Deuxième plainte active",
                    previous_request_status=ServiceRequest.Status.IN_PROGRESS,
                )

    def test_complaints_are_private_but_admin_can_list_all(self):
        created = self.post_complaint(self.client_user)
        complaint_id = created.json()["id"]

        owner = APIClient()
        owner.force_login(self.client_user)
        listing = owner.get("/api/v1/complaints/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()["count"], 1)
        self.assertEqual(listing.json()["results"][0]["id"], complaint_id)

        stranger = APIClient()
        stranger.force_login(self.other_client)
        self.assertEqual(
            stranger.get("/api/v1/complaints/").json()["count"],
            0,
        )
        self.assertEqual(
            stranger.get(f"/api/v1/complaints/{complaint_id}/").status_code,
            404,
        )

        provider = APIClient()
        provider.force_login(self.provider.user)
        self.assertEqual(
            provider.get(f"/api/v1/complaints/{complaint_id}/").status_code,
            404,
        )

        admin = APIClient()
        admin.force_login(self.admin_user)
        admin_listing = admin.get("/api/v1/complaints/admin/")
        self.assertEqual(admin_listing.status_code, 200)
        self.assertEqual(admin_listing.json()["count"], 1)
        result = admin_listing.json()["results"][0]
        self.assertEqual(result["reporter_id"], str(self.client_user.pk))
        self.assertEqual(result["reporter_role"], self.client_user.Role.CLIENT)

    def test_only_admin_can_transition_and_final_decision_requires_note(self):
        created = self.post_complaint(self.client_user)
        complaint_id = created.json()["id"]

        client_api = APIClient()
        client_api.force_login(self.client_user)
        self.assertEqual(
            client_api.post(
                f"/api/v1/complaints/admin/{complaint_id}/transition/",
                {"status": Complaint.Status.UNDER_REVIEW},
                format="json",
            ).status_code,
            403,
        )

        admin = APIClient()
        admin.force_login(self.admin_user)

        missing_note = admin.post(
            f"/api/v1/complaints/admin/{complaint_id}/transition/",
            {"status": Complaint.Status.RESOLVED},
            format="json",
        )
        self.assertEqual(missing_note.status_code, 400)

        reviewing = admin.post(
            f"/api/v1/complaints/admin/{complaint_id}/transition/",
            {
                "status": Complaint.Status.UNDER_REVIEW,
                "note": "Dossier pris en charge.",
            },
            format="json",
        )
        self.assertEqual(reviewing.status_code, 200)
        self.assertEqual(
            reviewing.json()["status"],
            Complaint.Status.UNDER_REVIEW,
        )
        self.service_request.refresh_from_db()
        self.assertEqual(
            self.service_request.status,
            ServiceRequest.Status.DISPUTED,
        )

    def test_admin_resolution_restores_previous_request_status_and_history(self):
        created = self.post_complaint(self.client_user)
        complaint_id = created.json()["id"]

        admin = APIClient()
        admin.force_login(self.admin_user)
        resolved = admin.post(
            f"/api/v1/complaints/admin/{complaint_id}/transition/",
            {
                "status": Complaint.Status.RESOLVED,
                "note": "Après vérification, l'intervention peut reprendre.",
            },
            format="json",
        )

        self.assertEqual(resolved.status_code, 200)
        self.assertEqual(
            resolved.json()["status"],
            Complaint.Status.RESOLVED,
        )
        self.assertEqual(
            resolved.json()["resolution_note"],
            "Après vérification, l'intervention peut reprendre.",
        )

        complaint = Complaint.objects.get(pk=complaint_id)
        self.assertIsNotNone(complaint.resolved_at)

        self.service_request.refresh_from_db()
        self.assertEqual(
            self.service_request.status,
            ServiceRequest.Status.IN_PROGRESS,
        )
        self.assertTrue(
            RequestStatusHistory.objects.filter(
                service_request=self.service_request,
                actor=self.admin_user,
                previous_status=ServiceRequest.Status.DISPUTED,
                new_status=ServiceRequest.Status.IN_PROGRESS,
            ).exists()
        )
        self.assertTrue(
            ComplaintStatusHistory.objects.filter(
                complaint=complaint,
                actor=self.admin_user,
                previous_status=Complaint.Status.OPEN,
                new_status=Complaint.Status.RESOLVED,
            ).exists()
        )

        repeat = admin.post(
            f"/api/v1/complaints/admin/{complaint_id}/transition/",
            {
                "status": Complaint.Status.REJECTED,
                "note": "Tentative après clôture.",
            },
            format="json",
        )
        self.assertEqual(repeat.status_code, 400)

    def test_unexpected_client_fields_are_rejected(self):
        response = self.post_complaint(
            self.client_user,
            status=Complaint.Status.RESOLVED,
            reporter_id=str(self.other_client.pk),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Complaint.objects.count(), 0)
