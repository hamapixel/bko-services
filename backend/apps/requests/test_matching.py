from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
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


class MatchingTests(TestCase):
    def setUp(self):
        self.client_user = get_user_model().objects.create_user(
            phone="+22310000000", password="Strong-password-2026!", phone_verified_at=timezone.now()
        )
        self.admin_user = get_user_model().objects.create_superuser(
            phone="+22310000001", password="Strong-admin-2026!"
        )
        city = City.objects.get(name="Bamako")
        commune = Commune.objects.create(city=city, name="Commune exemple")
        self.area = Neighborhood.objects.create(commune=commune, name="Quartier exemple")
        self.trade = Trade.objects.create(category=Category.objects.create(name="Maison"), name="Plomberie")
        self.next_phone = 10
        self.plan = SubscriptionPlan.objects.create(
            code="matching-test",
            name="Matching Test",
            price_xof=0,
            duration_days=30,
            can_receive_requests=True,
            can_receive_urgent_requests=True,
        )

    def request(self, priority="NORMAL"):
        return create_service_request(
            self.client_user.pk,
            trade=self.trade,
            neighborhood=self.area,
            title="Rue privée, détails confidentiels",
            description="Numéro de contact privé dans la description",
            address_detail="Adresse précise privée",
            priority=priority,
        )

    def provider(self, *, available=True, verified=True, phone_verified=True, trade=True, area=True, subscribed=True):
        phone = f"+2231{self.next_phone:07d}"
        self.next_phone += 1
        user = get_user_model().objects.create_user(
            phone=phone,
            password="Strong-password-2026!",
            role="PROVIDER",
            phone_verified_at=timezone.now() if phone_verified else None,
        )
        profile = ProviderProfile.objects.create(
            user=user,
            legal_name="Nom privé",
            display_name=f"Artisan {self.next_phone}",
            status=ProviderProfile.Status.VERIFIED if verified else ProviderProfile.Status.PENDING,
            is_available=available,
            verified_at=timezone.now() if verified else None,
        )
        if trade:
            profile.trades.add(self.trade)
        if area:
            profile.service_areas.add(self.area)
        if subscribed:
            now = timezone.now()
            ProviderSubscription.objects.create(
                provider=profile,
                plan=self.plan,
                starts_at=now - timedelta(minutes=1),
                ends_at=now + timedelta(days=30),
            )
        return profile

    def test_urgent_request_creates_at_most_five_private_offers(self):
        service_request = self.request("URGENT")
        profiles = [self.provider() for _ in range(6)]
        with self.assertRaises(PermissionDenied):
            dispatch_request(service_request.pk, self.client_user)
        self.assertEqual(dispatch_request(service_request.pk, self.admin_user), 5)
        service_request.refresh_from_db()
        self.assertEqual(service_request.status, ServiceRequest.Status.OFFERED)
        self.assertEqual(ServiceOffer.objects.filter(service_request=service_request).count(), 5)
        self.assertEqual(
            list(service_request.status_history.values_list("previous_status", "new_status")),
            [("", "CREATED"), ("CREATED", "SEARCHING"), ("SEARCHING", "OFFERED")],
        )
        with self.assertRaises(ValidationError):
            dispatch_request(service_request.pk, self.admin_user)

        own_client = APIClient()
        own_client.force_login(profiles[0].user)
        offer = own_client.get("/api/v1/providers/offers/").json()["results"][0]
        self.assertEqual(offer["trade_id"], str(self.trade.pk))
        self.assertEqual(offer["neighborhood_id"], str(self.area.pk))
        for private in ("address_detail", "description", "title", "phone", "client"):
            self.assertNotIn(private, offer)
        self.assertNotIn("confidentiels", str(offer))
        self.assertEqual(own_client.get(f"/api/v1/providers/offers/{offer['id']}/").status_code, 200)

        not_selected = APIClient()
        not_selected.force_login(profiles[5].user)
        self.assertEqual(not_selected.get("/api/v1/providers/offers/").json()["count"], 0)
        self.assertEqual(not_selected.get(f"/api/v1/providers/offers/{offer['id']}/").status_code, 404)
        self.assertEqual(APIClient().get(f"/api/v1/providers/offers/{offer['id']}/").status_code, 403)

    def test_normal_request_has_one_offer_and_excludes_ineligible_profiles(self):
        self.provider(available=False)
        self.provider(verified=False)
        self.provider(phone_verified=False)
        self.provider(trade=False)
        self.provider(area=False)
        self.provider(subscribed=False)
        selected = self.provider()
        service_request = self.request()
        self.trade.category.is_active = False
        self.trade.category.save(update_fields=["is_active"])
        with self.assertRaises(ValidationError):
            dispatch_request(service_request.pk, self.admin_user)
        service_request.refresh_from_db()
        self.assertEqual(service_request.status, ServiceRequest.Status.CREATED)
        self.trade.category.is_active = True
        self.trade.category.save(update_fields=["is_active"])
        self.assertEqual(dispatch_request(service_request.pk, self.admin_user), 1)
        self.assertEqual(ServiceOffer.objects.get(service_request=service_request).provider, selected)
        selected.user.role = selected.user.Role.CLIENT
        selected.user.save(update_fields=["role"])
        self.assertEqual(ServiceOffer.objects.count(), 1)
        own_client = APIClient()
        own_client.force_login(selected.user)
        self.assertEqual(own_client.get("/api/v1/providers/offers/").json()["count"], 0)

    def test_staff_without_dispatch_permission_cannot_create_offers(self):
        service_request = self.request()
        self.provider()
        staff = get_user_model().objects.create_user(
            phone="+22310000002", password="Strong-password-2026!", role="ADMIN", is_staff=True
        )
        with self.assertRaises(PermissionDenied):
            dispatch_request(service_request.pk, staff)
        self.assertEqual(ServiceOffer.objects.count(), 0)

    def test_search_without_candidates_can_be_retried_and_admin_action_dispatches(self):
        service_request = self.request()
        self.assertEqual(dispatch_request(service_request.pk, self.admin_user), 0)
        service_request.refresh_from_db()
        self.assertEqual(service_request.status, ServiceRequest.Status.SEARCHING)
        self.assertEqual(service_request.status_history.count(), 2)
        self.provider()
        admin_client = APIClient()
        admin_client.force_login(self.admin_user)
        response = admin_client.post(
            "/django-admin/requests/servicerequest/",
            {"action": "start_matching", "_selected_action": [str(service_request.pk)]},
        )
        self.assertEqual(response.status_code, 302)
        service_request.refresh_from_db()
        self.assertEqual(service_request.status, ServiceRequest.Status.OFFERED)
        self.assertEqual(service_request.status_history.count(), 3)
        self.assertEqual(ServiceOffer.objects.count(), 1)

    def test_offer_failure_rolls_back_status_and_history(self):
        service_request = self.request()
        self.provider()
        with patch("apps.requests.matching.ServiceOffer.objects.create", side_effect=IntegrityError("offer failed")):
            with self.assertRaises(IntegrityError):
                dispatch_request(service_request.pk, self.admin_user)
        service_request.refresh_from_db()
        self.assertEqual(service_request.status, ServiceRequest.Status.CREATED)
        self.assertEqual(RequestStatusHistory.objects.filter(service_request=service_request).count(), 1)
        self.assertEqual(ServiceOffer.objects.count(), 0)
