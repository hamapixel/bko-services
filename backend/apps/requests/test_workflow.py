from datetime import timedelta
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Category, Trade
from apps.locations.models import City, Commune, Neighborhood
from apps.providers.models import ProviderProfile
from apps.subscriptions.models import ProviderSubscription, SubscriptionPlan
from apps.subscriptions.models import ProviderSubscription, SubscriptionPlan

from .acceptance import accept_offer
from .matching import dispatch_request
from .models import RequestStatusHistory, ServiceOffer, ServiceRequest
from .services import create_service_request


class WorkflowAndIdorTests(TestCase):
    def setUp(self):
        self.client_user = get_user_model().objects.create_user(
            phone="+22340000000",
            password="Strong-password-2026!",
            phone_verified_at=timezone.now(),
        )
        self.other_client_user = get_user_model().objects.create_user(
            phone="+22340000001",
            password="Strong-password-2026!",
            phone_verified_at=timezone.now(),
        )
        self.admin_user = get_user_model().objects.create_superuser(
            phone="+22340000002",
            password="Strong-admin-2026!",
        )

        city = City.objects.get(name="Bamako")
        commune = Commune.objects.create(city=city, name="Commune workflow")
        self.area = Neighborhood.objects.create(commune=commune, name="Quartier workflow")
        self.trade = Trade.objects.create(
            category=Category.objects.create(name="Intervention"),
            name="Climatisation",
        )
        self.plan = SubscriptionPlan.objects.create(
            code="workflow-test",
            name="Workflow Test",
            price_xof=0,
            duration_days=30,
            can_receive_requests=True,
            can_receive_urgent_requests=True,
        )

        self.provider = self.create_provider("+22340000010", "Prestataire attribué")
        self.other_provider = self.create_provider("+22340000011", "Prestataire étranger")

        self.service_request = create_service_request(
            self.client_user.pk,
            trade=self.trade,
            neighborhood=self.area,
            title="Climatiseur en panne",
            description="Le climatiseur ne démarre plus.",
            address_detail="Porte verte, près du marché.",
            priority=ServiceRequest.Priority.URGENT,
        )
        self.assertEqual(dispatch_request(self.service_request.pk, self.admin_user), 2)

        offer = ServiceOffer.objects.get(
            service_request=self.service_request,
            provider=self.provider,
        )
        accept_offer(offer.pk, self.provider.user)
        self.service_request.refresh_from_db()

    def create_provider(self, phone, display_name):
        user = get_user_model().objects.create_user(
            phone=phone,
            password="Strong-password-2026!",
            role="PROVIDER",
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
        now = timezone.now()
        ProviderSubscription.objects.create(
            provider=profile,
            plan=self.plan,
            starts_at=now - timedelta(minutes=1),
            ends_at=now + timedelta(days=30),
        )
        return profile

    def test_provider_sees_only_assigned_intervention_and_private_details(self):
        assigned = APIClient()
        assigned.force_login(self.provider.user)

        listing = assigned.get("/api/v1/providers/interventions/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()["count"], 1)

        detail = assigned.get(f"/api/v1/providers/interventions/{self.service_request.pk}/")
        self.assertEqual(detail.status_code, 200)
        body = detail.json()
        self.assertEqual(body["address_detail"], "Porte verte, près du marché.")
        self.assertEqual(body["client_phone"], self.client_user.phone)

        stranger = APIClient()
        stranger.force_login(self.other_provider.user)
        self.assertEqual(stranger.get("/api/v1/providers/interventions/").json()["count"], 0)
        self.assertEqual(
            stranger.get(f"/api/v1/providers/interventions/{self.service_request.pk}/").status_code,
            404,
        )

    def test_client_sees_assignment_but_other_client_gets_404(self):
        owner = APIClient()
        owner.force_login(self.client_user)
        response = owner.get(f"/api/v1/requests/{self.service_request.pk}/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["assigned_provider_id"], str(self.provider.pk))
        self.assertEqual(body["assigned_provider_display_name"], self.provider.display_name)
        self.assertEqual(body["assigned_provider_phone"], self.provider.user.phone)

        stranger = APIClient()
        stranger.force_login(self.other_client_user)
        self.assertEqual(stranger.get(f"/api/v1/requests/{self.service_request.pk}/").status_code, 404)

    def test_provider_must_follow_workflow_in_order(self):
        api = APIClient()
        api.force_login(self.provider.user)

        invalid = api.post(
            f"/api/v1/providers/interventions/{self.service_request.pk}/transition/",
            {"status": ServiceRequest.Status.ARRIVED},
            format="json",
        )
        self.assertEqual(invalid.status_code, 400)

        sequence = [
            ServiceRequest.Status.EN_ROUTE,
            ServiceRequest.Status.ARRIVED,
            ServiceRequest.Status.IN_PROGRESS,
            ServiceRequest.Status.PROVIDER_COMPLETED,
        ]
        for target in sequence:
            response = api.post(
                f"/api/v1/providers/interventions/{self.service_request.pk}/transition/",
                {"status": target},
                format="json",
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], target)

        self.service_request.refresh_from_db()
        self.assertEqual(self.service_request.status, ServiceRequest.Status.PROVIDER_COMPLETED)

        history = list(
            RequestStatusHistory.objects.filter(service_request=self.service_request)
            .values_list("previous_status", "new_status")
        )
        self.assertEqual(
            history[-4:],
            [
                ("ACCEPTED", "EN_ROUTE"),
                ("EN_ROUTE", "ARRIVED"),
                ("ARRIVED", "IN_PROGRESS"),
                ("IN_PROGRESS", "PROVIDER_COMPLETED"),
            ],
        )

    def test_unassigned_provider_cannot_transition_foreign_request(self):
        api = APIClient()
        api.force_login(self.other_provider.user)
        response = api.post(
            f"/api/v1/providers/interventions/{self.service_request.pk}/transition/",
            {"status": ServiceRequest.Status.EN_ROUTE},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.service_request.refresh_from_db()
        self.assertEqual(self.service_request.status, ServiceRequest.Status.ACCEPTED)

    def test_only_client_owner_can_confirm_provider_completion(self):
        provider_api = APIClient()
        provider_api.force_login(self.provider.user)
        for target in (
            ServiceRequest.Status.EN_ROUTE,
            ServiceRequest.Status.ARRIVED,
            ServiceRequest.Status.IN_PROGRESS,
            ServiceRequest.Status.PROVIDER_COMPLETED,
        ):
            self.assertEqual(
                provider_api.post(
                    f"/api/v1/providers/interventions/{self.service_request.pk}/transition/",
                    {"status": target},
                    format="json",
                ).status_code,
                200,
            )

        stranger = APIClient()
        stranger.force_login(self.other_client_user)
        self.assertEqual(
            stranger.post(f"/api/v1/requests/{self.service_request.pk}/confirm/").status_code,
            404,
        )

        provider_cannot_confirm = provider_api.post(
            f"/api/v1/requests/{self.service_request.pk}/confirm/"
        )
        self.assertEqual(provider_cannot_confirm.status_code, 404)

        owner = APIClient()
        owner.force_login(self.client_user)
        confirmed = owner.post(f"/api/v1/requests/{self.service_request.pk}/confirm/")
        self.assertEqual(confirmed.status_code, 200)
        self.assertEqual(confirmed.json()["status"], ServiceRequest.Status.CLIENT_CONFIRMED)

        repeat = owner.post(f"/api/v1/requests/{self.service_request.pk}/confirm/")
        self.assertEqual(repeat.status_code, 400)

        self.service_request.refresh_from_db()
        self.assertEqual(self.service_request.status, ServiceRequest.Status.CLIENT_CONFIRMED)
        self.assertEqual(
            RequestStatusHistory.objects.filter(
                service_request=self.service_request,
                previous_status=ServiceRequest.Status.PROVIDER_COMPLETED,
                new_status=ServiceRequest.Status.CLIENT_CONFIRMED,
                actor=self.client_user,
            ).count(),
            1,
        )
