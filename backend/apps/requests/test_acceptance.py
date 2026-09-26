from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Category, Trade
from apps.locations.models import City, Commune, Neighborhood
from apps.providers.models import ProviderProfile
from apps.subscriptions.models import ProviderSubscription, SubscriptionPlan

from .matching import dispatch_request
from .models import RequestStatusHistory, ServiceOffer, ServiceRequest
from .services import create_service_request


class AcceptanceTests(TestCase):
    def setUp(self):
        self.client_user = get_user_model().objects.create_user(
            phone="+22320000000",
            password="Strong-password-2026!",
            phone_verified_at=timezone.now(),
        )
        self.admin_user = get_user_model().objects.create_superuser(
            phone="+22320000001",
            password="Strong-admin-2026!",
        )
        city = City.objects.get(name="Bamako")
        commune = Commune.objects.create(city=city, name="Commune acceptation")
        self.area = Neighborhood.objects.create(commune=commune, name="Quartier acceptation")
        self.trade = Trade.objects.create(
            category=Category.objects.create(name="Dépannage"),
            name="Électricité",
        )
        self.next_phone = 10
        self.plan = SubscriptionPlan.objects.create(
            code="acceptance-test",
            name="Acceptance Test",
            price_xof=0,
            duration_days=30,
            can_receive_requests=True,
            can_receive_urgent_requests=True,
        )

    def create_request(self):
        return create_service_request(
            self.client_user.pk,
            trade=self.trade,
            neighborhood=self.area,
            title="Panne électrique",
            description="Détails privés",
            address_detail="Adresse privée",
            priority=ServiceRequest.Priority.URGENT,
        )

    def create_provider(self):
        phone = f"+2232{self.next_phone:07d}"
        self.next_phone += 1
        user = get_user_model().objects.create_user(
            phone=phone,
            password="Strong-password-2026!",
            role="PROVIDER",
            phone_verified_at=timezone.now(),
        )
        profile = ProviderProfile.objects.create(
            user=user,
            legal_name="Nom privé",
            display_name=f"Prestataire {self.next_phone}",
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

    def prepare_offers(self):
        providers = [self.create_provider(), self.create_provider()]
        service_request = self.create_request()
        self.assertEqual(ServiceOffer.objects.filter(service_request=service_request).count(), 2)
        offers = list(ServiceOffer.objects.filter(service_request=service_request).order_by("created_at", "id"))
        return service_request, providers, offers

    def test_offer_exposes_safe_job_metadata_without_private_contact_details(self):
        service_request, providers, offers = self.prepare_offers()
        api = APIClient()
        api.force_login(providers[0].user)

        response = api.get(f"/api/v1/providers/offers/{offers[0].pk}/")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["request_id"], str(service_request.pk))
        self.assertEqual(body["trade_name"], self.trade.name)
        self.assertEqual(body["neighborhood_name"], self.area.name)
        self.assertEqual(body["commune_name"], self.area.commune.name)
        for private in ("title", "description", "address_detail", "client_phone"):
            self.assertNotIn(private, body)
        self.assertNotIn(self.client_user.phone, str(body))
        self.assertNotIn(service_request.title, str(body))
        self.assertNotIn(service_request.description, str(body))
        self.assertNotIn(service_request.address_detail, str(body))

    def test_provider_accepts_own_offer_and_competitors_are_cancelled(self):
        service_request, providers, offers = self.prepare_offers()
        api = APIClient()
        api.force_login(providers[0].user)

        response = api.post(f"/api/v1/providers/offers/{offers[0].pk}/accept/")

        self.assertEqual(response.status_code, 200)
        service_request.refresh_from_db()
        offers[0].refresh_from_db()
        offers[1].refresh_from_db()

        self.assertEqual(service_request.status, ServiceRequest.Status.ACCEPTED)
        self.assertEqual(service_request.assigned_provider, providers[0])
        self.assertEqual(offers[0].status, ServiceOffer.Status.ACCEPTED)
        self.assertEqual(offers[1].status, ServiceOffer.Status.CANCELLED)
        self.assertEqual(
            list(service_request.status_history.values_list("previous_status", "new_status")),
            [
                ("", "CREATED"),
                ("CREATED", "SEARCHING"),
                ("SEARCHING", "OFFERED"),
                ("OFFERED", "ACCEPTED"),
            ],
        )
        self.assertEqual(response.json()["assigned_provider_id"], str(providers[0].pk))

    def test_provider_cannot_accept_another_providers_offer(self):
        _, providers, offers = self.prepare_offers()
        api = APIClient()
        api.force_login(providers[1].user)

        response = api.post(f"/api/v1/providers/offers/{offers[0].pk}/accept/")

        self.assertEqual(response.status_code, 404)

    def test_offer_cannot_be_accepted_after_provider_reaches_plan_capacity(self):
        _, providers, offers = self.prepare_offers()
        self.plan.max_active_jobs = 1
        self.plan.save(update_fields=["max_active_jobs"])
        occupied = ServiceRequest.objects.create(
            client=self.client_user, trade=self.trade, neighborhood=self.area,
            assigned_provider=providers[0], status=ServiceRequest.Status.IN_PROGRESS,
            title="Autre intervention", description="Détails", address_detail="Adresse",
        )
        api = APIClient()
        api.force_login(providers[0].user)
        self.assertEqual(api.get("/api/v1/providers/offers/").json()["count"], 0)
        response = api.post(f"/api/v1/providers/offers/{offers[0].pk}/accept/")
        self.assertEqual(response.status_code, 400)
        offers[0].refresh_from_db()
        self.assertEqual(offers[0].status, ServiceOffer.Status.PENDING)
        occupied.status = ServiceRequest.Status.PROVIDER_COMPLETED
        occupied.save(update_fields=["status"])
        self.assertEqual(api.get("/api/v1/providers/offers/").json()["count"], 1)

    def test_second_provider_cannot_win_after_first_acceptance(self):
        service_request, providers, offers = self.prepare_offers()

        first = APIClient()
        first.force_login(providers[0].user)
        self.assertEqual(first.post(f"/api/v1/providers/offers/{offers[0].pk}/accept/").status_code, 200)

        second = APIClient()
        second.force_login(providers[1].user)
        response = second.post(f"/api/v1/providers/offers/{offers[1].pk}/accept/")

        self.assertEqual(response.status_code, 400)
        service_request.refresh_from_db()
        offers[0].refresh_from_db()
        offers[1].refresh_from_db()

        self.assertEqual(service_request.assigned_provider, providers[0])
        self.assertEqual(ServiceOffer.objects.filter(service_request=service_request, status="ACCEPTED").count(), 1)
        self.assertEqual(offers[0].status, ServiceOffer.Status.ACCEPTED)
        self.assertEqual(offers[1].status, ServiceOffer.Status.CANCELLED)
        self.assertEqual(
            RequestStatusHistory.objects.filter(
                service_request=service_request,
                previous_status="OFFERED",
                new_status="ACCEPTED",
            ).count(),
            1,
        )

    def test_provider_is_revalidated_at_acceptance_time(self):
        service_request, providers, offers = self.prepare_offers()
        providers[0].is_available = False
        providers[0].save(update_fields=["is_available"])

        api = APIClient()
        api.force_login(providers[0].user)
        response = api.post(f"/api/v1/providers/offers/{offers[0].pk}/accept/")

        self.assertEqual(response.status_code, 400)
        service_request.refresh_from_db()
        offers[0].refresh_from_db()

        self.assertEqual(service_request.status, ServiceRequest.Status.OFFERED)
        self.assertIsNone(service_request.assigned_provider)
        self.assertEqual(offers[0].status, ServiceOffer.Status.PENDING)

    def test_database_rejects_two_accepted_offers_for_same_request(self):
        service_request, providers, offers = self.prepare_offers()
        offers[0].status = ServiceOffer.Status.ACCEPTED
        offers[0].save(update_fields=["status"])

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ServiceOffer.objects.filter(pk=offers[1].pk).update(status=ServiceOffer.Status.ACCEPTED)

        self.assertEqual(
            ServiceOffer.objects.filter(service_request=service_request, status=ServiceOffer.Status.ACCEPTED).count(),
            1,
        )
