"""A complete API journey that must pass on both SQLite and PostgreSQL."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Category, Trade
from apps.locations.models import City, Commune, Neighborhood
from apps.notifications.models import Notification
from apps.providers.models import ProviderProfile
from apps.reviews.models import Review
from apps.subscriptions.models import ProviderSubscription, SubscriptionPlan

from .models import RequestStatusHistory, ServiceOffer, ServiceRequest


class ClientProviderJourneyTests(TestCase):
    def test_request_offer_work_review_and_private_data(self):
        User = get_user_model()
        client_user = User.objects.create_user(
            phone="+22331000000", password="Strong-password-2026!",
            phone_verified_at=timezone.now(),
        )
        provider_user = User.objects.create_user(
            phone="+22331000001", password="Strong-password-2026!",
            role="PROVIDER", phone_verified_at=timezone.now(),
        )
        other_user = User.objects.create_user(
            phone="+22331000002", password="Strong-password-2026!",
            role="PROVIDER", phone_verified_at=timezone.now(),
        )
        city = City.objects.get(name="Bamako")
        commune = Commune.objects.create(city=city, name="Commune parcours")
        neighborhood = Neighborhood.objects.create(commune=commune, name="Quartier parcours")
        trade = Trade.objects.create(
            category=Category.objects.create(name="Maison parcours"), name="Plomberie parcours",
        )
        provider = ProviderProfile.objects.create(
            user=provider_user, legal_name="Nom privé", display_name="Artisan parcours",
            status=ProviderProfile.Status.VERIFIED, is_available=True,
            verified_at=timezone.now(),
        )
        provider.trades.add(trade)
        provider.service_areas.add(neighborhood)
        other = ProviderProfile.objects.create(
            user=other_user, legal_name="Autre nom privé", display_name="Autre artisan",
            status=ProviderProfile.Status.VERIFIED, is_available=True,
            verified_at=timezone.now(),
        )
        other.trades.add(trade)  # Same trade, but not the client's neighborhood.
        plan = SubscriptionPlan.objects.create(
            code="journey-plan", name="Parcours test", price_xof=2000,
            duration_days=30, can_receive_requests=True,
            can_receive_urgent_requests=False,
        )
        now = timezone.now()
        ProviderSubscription.objects.create(
            provider=provider, plan=plan,
            starts_at=now - timedelta(minutes=1), ends_at=now + timedelta(days=30),
        )

        client = APIClient(enforce_csrf_checks=True)
        client.force_login(client_user)
        client_csrf = client.get("/api/v1/auth/csrf/").json()["csrfToken"]
        created = client.post(
            "/api/v1/requests/",
            {
                "trade": str(trade.pk), "neighborhood": str(neighborhood.pk),
                "title": "Fuite dans la cuisine", "description": "Détails privés de la fuite",
                "address_detail": "Adresse exacte privée", "priority": "NORMAL",
            },
            format="json", HTTP_X_CSRFTOKEN=client_csrf,
        )
        self.assertEqual(created.status_code, 201, created.content)
        request_id = created.json()["id"]
        self.assertEqual(created.json()["status"], ServiceRequest.Status.OFFERED)
        self.assertEqual(ServiceOffer.objects.filter(service_request_id=request_id).count(), 1)

        provider_api = APIClient(enforce_csrf_checks=True)
        provider_api.force_login(provider_user)
        provider_csrf = provider_api.get("/api/v1/auth/csrf/").json()["csrfToken"]
        offers = provider_api.get("/api/v1/providers/offers/").json()
        self.assertEqual(offers["count"], 1)
        offer = offers["results"][0]
        for secret in ("title", "description", "address_detail", "client_phone"):
            self.assertNotIn(secret, offer)
        self.assertNotIn("Adresse exacte privée", str(offer))

        other_api = APIClient()
        other_api.force_login(other_user)
        self.assertEqual(other_api.get("/api/v1/providers/offers/").json()["count"], 0)
        self.assertEqual(
            other_api.get(f"/api/v1/providers/offers/{offer['id']}/").status_code, 404,
        )
        accepted = provider_api.post(
            f"/api/v1/providers/offers/{offer['id']}/accept/",
            HTTP_X_CSRFTOKEN=provider_csrf,
        )
        self.assertEqual(accepted.status_code, 200, accepted.content)
        intervention = provider_api.get(f"/api/v1/providers/interventions/{request_id}/")
        self.assertEqual(intervention.status_code, 200)
        self.assertEqual(intervention.json()["address_detail"], "Adresse exacte privée")
        self.assertEqual(intervention.json()["client_phone"], client_user.phone)

        for target in (
            ServiceRequest.Status.EN_ROUTE,
            ServiceRequest.Status.ARRIVED,
            ServiceRequest.Status.IN_PROGRESS,
            ServiceRequest.Status.PROVIDER_COMPLETED,
        ):
            advanced = provider_api.post(
                f"/api/v1/providers/interventions/{request_id}/transition/",
                {"status": target}, format="json", HTTP_X_CSRFTOKEN=provider_csrf,
            )
            self.assertEqual(advanced.status_code, 200, advanced.content)
            self.assertEqual(advanced.json()["status"], target)

        confirmed = client.post(
            f"/api/v1/requests/{request_id}/confirm/", HTTP_X_CSRFTOKEN=client_csrf,
        )
        self.assertEqual(confirmed.status_code, 200, confirmed.content)
        reviewed = client.post(
            f"/api/v1/requests/{request_id}/review/",
            {"rating": 5, "comment": "Intervention terminée."},
            format="json", HTTP_X_CSRFTOKEN=client_csrf,
        )
        self.assertEqual(reviewed.status_code, 201, reviewed.content)
        self.assertEqual(Review.objects.get(service_request_id=request_id).provider, provider)
        self.assertTrue(Notification.objects.filter(
            recipient=provider_user, service_request_id=request_id,
            kind=Notification.Kind.REVIEW_RECEIVED,
        ).exists())
        self.assertTrue(client.get(f"/api/v1/requests/{request_id}/").json()["has_review"])
        self.assertEqual(
            list(RequestStatusHistory.objects.filter(service_request_id=request_id)
                 .values_list("new_status", flat=True)),
            ["CREATED", "SEARCHING", "OFFERED", "ACCEPTED", "EN_ROUTE", "ARRIVED",
             "IN_PROGRESS", "PROVIDER_COMPLETED", "CLIENT_CONFIRMED"],
        )
