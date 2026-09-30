from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Category, Trade
from apps.locations.models import City, Commune, Neighborhood, Region
from apps.providers.models import ProviderProfile
from apps.subscriptions.models import ProviderSubscription, SubscriptionPlan

from .models import ServiceOffer, ServiceRequest
from .services import create_service_request


class CrossCommuneMatchingTests(TestCase):
    def setUp(self):
        self.client_user = get_user_model().objects.create_user(
            phone="+22330000000",
            password="Strong-password-2026!",
            phone_verified_at=timezone.now(),
        )
        self.region = Region.objects.create(name="Zone matching test")
        self.city = City.objects.create(name="Ville matching test", region=self.region)
        self.request_commune = Commune.objects.create(city=self.city, name="Commune cible")
        self.other_commune = Commune.objects.create(city=self.city, name="Commune voisine")
        self.third_commune = Commune.objects.create(city=self.city, name="Commune distante")
        self.request_area = Neighborhood.objects.create(
            commune=self.request_commune, name="Quartier cible"
        )
        self.same_commune_area = Neighborhood.objects.create(
            commune=self.request_commune, name="Quartier voisin"
        )
        self.other_area = Neighborhood.objects.create(
            commune=self.other_commune, name="Quartier autre commune"
        )
        self.third_area = Neighborhood.objects.create(
            commune=self.third_commune, name="Quartier troisième commune"
        )
        self.trade = Trade.objects.create(
            category=Category.objects.create(name="Bâtiment matching test"),
            name="Plombier matching test",
        )
        self.plan = SubscriptionPlan.objects.create(
            code="cross-commune-test",
            name="Cross Commune Test",
            price_xof=0,
            duration_days=30,
            can_receive_requests=True,
            can_receive_urgent_requests=True,
        )
        self.next_phone = 1

    def provider(self, area, *, travel_to=None):
        phone = f"+2233{self.next_phone:07d}"
        self.next_phone += 1
        user = get_user_model().objects.create_user(
            phone=phone,
            password="Strong-password-2026!",
            role="PROVIDER",
            phone_verified_at=timezone.now(),
        )
        profile = ProviderProfile.objects.create(
            user=user,
            legal_name=f"Prestataire {self.next_phone}",
            display_name=f"Prestataire {self.next_phone}",
            status=ProviderProfile.Status.VERIFIED,
            is_available=True,
            verified_at=timezone.now(),
        )
        profile.trades.add(self.trade)
        profile.service_areas.add(area)
        if travel_to:
            profile.travel_communes.add(*travel_to)
        now = timezone.now()
        ProviderSubscription.objects.create(
            provider=profile,
            plan=self.plan,
            starts_at=now - timedelta(minutes=1),
            ends_at=now + timedelta(days=30),
        )
        return profile

    def create_request(self):
        return create_service_request(
            self.client_user.pk,
            trade=self.trade,
            neighborhood=self.request_area,
            title="Robinet cassé",
            description="Le tuyau est cassé",
            address_detail="Adresse privée",
            priority="NORMAL",
        )

    def test_matching_priority_is_quartier_then_commune_then_authorized_travel(self):
        exact = self.provider(self.request_area)
        same_commune = self.provider(self.same_commune_area)
        travel = self.provider(self.other_area, travel_to=[self.request_commune])
        unrelated = self.provider(self.third_area)

        service_request = self.create_request()

        offered = list(
            service_request.offers.values_list("provider_id", flat=True)
        )
        self.assertEqual(offered, [exact.pk, same_commune.pk, travel.pk])
        self.assertNotIn(unrelated.pk, offered)
        self.assertEqual(service_request.status, ServiceRequest.Status.OFFERED)

    def test_same_commune_is_used_before_authorized_travel_when_limit_is_full(self):
        exact = [self.provider(self.request_area) for _ in range(2)]
        same_commune = self.provider(self.same_commune_area)
        travel = self.provider(self.other_area, travel_to=[self.request_commune])

        service_request = self.create_request()
        offered = set(service_request.offers.values_list("provider_id", flat=True))

        self.assertEqual(offered, {exact[0].pk, exact[1].pk, same_commune.pk})
        self.assertNotIn(travel.pk, offered)

    def test_other_commune_is_not_used_without_explicit_authorization(self):
        distant = self.provider(self.other_area)

        service_request = self.create_request()

        self.assertEqual(service_request.status, ServiceRequest.Status.SEARCHING)
        self.assertFalse(service_request.offers.exists())
        self.assertFalse(distant.travel_communes.exists())

    def test_first_authorized_travel_provider_wins_and_other_offer_is_cancelled(self):
        first = self.provider(self.other_area, travel_to=[self.request_commune])
        second = self.provider(self.third_area, travel_to=[self.request_commune])
        service_request = self.create_request()
        first_offer = service_request.offers.get(provider=first)
        second_offer = service_request.offers.get(provider=second)

        api = APIClient()
        api.force_login(first.user)
        response = api.post(
            f"/api/v1/providers/offers/{first_offer.pk}/accept/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        service_request.refresh_from_db()
        first_offer.refresh_from_db()
        second_offer.refresh_from_db()
        self.assertEqual(service_request.assigned_provider, first)
        self.assertEqual(service_request.status, ServiceRequest.Status.ACCEPTED)
        self.assertEqual(first_offer.status, ServiceOffer.Status.ACCEPTED)
        self.assertEqual(second_offer.status, ServiceOffer.Status.CANCELLED)

    def test_adding_travel_commune_retries_waiting_request(self):
        profile = self.provider(self.other_area)
        service_request = self.create_request()
        self.assertEqual(service_request.status, ServiceRequest.Status.SEARCHING)
        self.assertFalse(service_request.offers.exists())

        api = APIClient()
        api.force_login(profile.user)
        with self.captureOnCommitCallbacks(execute=True):
            response = api.patch(
                "/api/v1/providers/travel-communes/",
                {"commune_ids": [str(self.request_commune.pk)]},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        profile.refresh_from_db()
        self.assertTrue(profile.travel_communes.filter(pk=self.request_commune.pk).exists())
        service_request.refresh_from_db()
        self.assertEqual(service_request.status, ServiceRequest.Status.OFFERED)
        self.assertEqual(service_request.offers.get().provider, profile)
