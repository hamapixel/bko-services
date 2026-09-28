from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Category, Trade
from apps.locations.models import City, Commune, Neighborhood, Region
from apps.notifications.models import Notification
from apps.providers.models import ProviderProfile
from apps.subscriptions.services import activate_subscription
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
        service_request = ServiceRequest.objects.create(
            client=self.client_user,
            trade=self.trade,
            neighborhood=self.area,
            title="Rue privée, détails confidentiels",
            description="Numéro de contact privé dans la description",
            address_detail="Adresse précise privée",
            priority=priority,
        )
        RequestStatusHistory.objects.create(
            service_request=service_request, actor=self.client_user,
            previous_status="", new_status=ServiceRequest.Status.CREATED,
        )
        return service_request

    def test_client_creation_dispatches_to_matching_plumber_immediately(self):
        plumber = self.provider()
        other_trade = Trade.objects.create(category=self.trade.category, name="Électricité")
        plumber.trades.add(other_trade)
        service_request = create_service_request(
            self.client_user.pk, trade=self.trade, neighborhood=self.area,
            title="Fuite à réparer", description="Fuite dans la salle de bain",
            address_detail="Porte bleue", priority="NORMAL",
        )
        self.assertEqual(service_request.status, ServiceRequest.Status.OFFERED)
        self.assertEqual(service_request.offers.get().provider, plumber)
        provider_client = APIClient()
        provider_client.force_login(plumber.user)
        offers = provider_client.get("/api/v1/providers/offers/").json()
        self.assertEqual(offers["count"], 1)
        self.assertEqual(offers["results"][0]["trade_name"], "Plomberie")

    def test_matching_skips_full_provider_and_releases_slot_after_work_is_finished(self):
        self.plan.max_active_jobs = 1
        self.plan.save(update_fields=["max_active_jobs"])
        busy = self.provider()
        available = self.provider()
        occupied = ServiceRequest.objects.create(
            client=self.client_user, trade=self.trade, neighborhood=self.area,
            assigned_provider=busy, status=ServiceRequest.Status.IN_PROGRESS,
            title="Intervention en cours", description="Détails", address_detail="Adresse",
        )
        waiting = self.request()
        self.assertEqual(dispatch_request(waiting.pk, self.admin_user), 1)
        self.assertEqual(waiting.offers.get().provider, available)

        occupied.status = ServiceRequest.Status.PROVIDER_COMPLETED
        occupied.save(update_fields=["status"])
        next_request = self.request()
        self.assertEqual(dispatch_request(next_request.pk, self.admin_user), 2)
        self.assertIn(busy, [offer.provider for offer in next_request.offers.all()])

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

        selected_provider_ids = set(service_request.offers.values_list("provider_id", flat=True))
        own_provider = next(profile for profile in profiles if profile.pk in selected_provider_ids)
        not_selected_provider = next(profile for profile in profiles if profile.pk not in selected_provider_ids)
        own_client = APIClient()
        own_client.force_login(own_provider.user)
        offer = own_client.get("/api/v1/providers/offers/").json()["results"][0]
        self.assertEqual(offer["trade_id"], str(self.trade.pk))
        self.assertEqual(offer["neighborhood_id"], str(self.area.pk))
        for private in ("address_detail", "description", "title", "phone", "client"):
            self.assertNotIn(private, offer)
        self.assertNotIn("confidentiels", str(offer))
        self.assertEqual(own_client.get(f"/api/v1/providers/offers/{offer['id']}/").status_code, 200)

        not_selected = APIClient()
        not_selected.force_login(not_selected_provider.user)
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

    def test_normal_request_prioritizes_exact_quartier_then_same_commune(self):
        neighboring_area = Neighborhood.objects.create(
            commune=self.area.commune, name="Quartier voisin",
        )
        other_commune = Commune.objects.create(city=self.area.commune.city, name="Autre commune")
        distant_area = Neighborhood.objects.create(commune=other_commune, name="Quartier distant")
        exact = self.provider()
        neighbors = [self.provider(area=False) for _ in range(3)]
        for profile in neighbors:
            profile.service_areas.add(neighboring_area)
        distant = self.provider(area=False)
        distant.service_areas.add(distant_area)
        wrong_trade = self.provider(area=False, trade=False)
        wrong_trade.service_areas.add(neighboring_area)

        service_request = create_service_request(
            self.client_user.pk, trade=self.trade, neighborhood=self.area,
            title="Fuite", description="Réparation", address_detail="Adresse privée", priority="NORMAL",
        )
        offered = list(service_request.offers.order_by("created_at", "id").values_list("provider_id", flat=True))
        self.assertEqual(len(offered), 3)
        self.assertEqual(offered[0], exact.pk)
        self.assertEqual(set(offered[1:]), {neighbors[0].pk, neighbors[1].pk})
        self.assertNotIn(distant.pk, offered)
        self.assertNotIn(wrong_trade.pk, offered)

    def test_waiting_request_retries_when_provider_serves_neighboring_quartier(self):
        neighboring_area = Neighborhood.objects.create(commune=self.area.commune, name="Quartier voisin")
        profile = self.provider(area=False, available=False)
        profile.service_areas.add(neighboring_area)
        service_request = create_service_request(
            self.client_user.pk, trade=self.trade, neighborhood=self.area,
            title="Fuite", description="Réparation", address_detail="Adresse privée", priority="NORMAL",
        )
        self.assertEqual(service_request.status, ServiceRequest.Status.SEARCHING)
        api = APIClient()
        api.force_login(profile.user)
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(api.patch("/api/v1/providers/availability/", {"is_available": True}, format="json").status_code, 200)
        self.assertEqual(service_request.offers.get().provider, profile)

    def test_normal_request_reserves_one_offer_for_neighboring_quartier(self):
        neighboring_area = Neighborhood.objects.create(commune=self.area.commune, name="Quartier voisin")
        exact = [self.provider() for _ in range(3)]
        neighbor = self.provider(area=False)
        neighbor.service_areas.add(neighboring_area)
        service_request = create_service_request(
            self.client_user.pk, trade=self.trade, neighborhood=self.area,
            title="Fuite", description="Réparation", address_detail="Adresse privée", priority="NORMAL",
        )
        offered = list(service_request.offers.order_by("created_at", "id").values_list("provider_id", flat=True))
        self.assertEqual(len(offered), 3)
        self.assertIn(neighbor.pk, offered)
        self.assertEqual(len(set(offered) & {profile.pk for profile in exact}), 2)

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
        self.assertEqual(Notification.objects.filter(
            recipient=self.admin_user, service_request=service_request,
            kind=Notification.Kind.REQUEST_UNMATCHED,
        ).count(), 1)
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
        self.assertFalse(Notification.objects.filter(
            recipient=self.admin_user, service_request=service_request,
            kind=Notification.Kind.REQUEST_UNMATCHED, read_at__isnull=True,
        ).exists())

    def test_waiting_request_is_sent_when_provider_becomes_available(self):
        profile = self.provider(available=False)
        service_request = create_service_request(
            self.client_user.pk, trade=self.trade, neighborhood=self.area,
            title="Fuite", description="Fuite à réparer", address_detail="Près de la pharmacie",
            priority="NORMAL",
        )
        self.assertEqual(service_request.status, ServiceRequest.Status.SEARCHING)
        api = APIClient()
        api.force_login(profile.user)
        with self.captureOnCommitCallbacks(execute=True):
            response = api.patch("/api/v1/providers/availability/", {"is_available": True}, format="json")
        self.assertEqual(response.status_code, 200)
        service_request.refresh_from_db()
        self.assertEqual(service_request.status, ServiceRequest.Status.OFFERED)
        self.assertEqual(service_request.offers.get().provider, profile)

    def test_waiting_request_is_sent_after_subscription_activation(self):
        profile = self.provider(subscribed=False)
        service_request = create_service_request(
            self.client_user.pk, trade=self.trade, neighborhood=self.area,
            title="Fuite", description="Fuite à réparer", address_detail="Près de la pharmacie",
            priority="NORMAL",
        )
        with self.captureOnCommitCallbacks(execute=True):
            activate_subscription(profile.pk, self.admin_user, plan_id=self.plan.pk)
        service_request.refresh_from_db()
        self.assertEqual(service_request.status, ServiceRequest.Status.OFFERED)
        self.assertEqual(service_request.offers.get().provider, profile)

    def test_matching_uses_exact_quartier_outside_bamako(self):
        kayes = Region.objects.get(name="Kayes")
        kidal = Region.objects.get(name="Kidal")
        kayes_area = Neighborhood.objects.create(
            commune=Commune.objects.create(city=City.objects.create(name="Kayes", region=kayes), name="Commune Kayes"),
            name="Quartier Kayes",
        )
        kidal_area = Neighborhood.objects.create(
            commune=Commune.objects.create(city=City.objects.create(name="Kidal", region=kidal), name="Commune Kidal"),
            name="Quartier Kidal",
        )
        kayes_provider = self.provider(area=False)
        kayes_provider.service_areas.add(kayes_area)
        kidal_provider = self.provider(area=False)
        kidal_provider.service_areas.add(kidal_area)
        for area, provider in ((kayes_area, kayes_provider), (kidal_area, kidal_provider)):
            request = create_service_request(
                self.client_user.pk, trade=self.trade, neighborhood=area,
                title="Intervention", description="Une réparation", address_detail="Adresse privée",
                priority="NORMAL",
            )
            self.assertEqual(request.status, ServiceRequest.Status.OFFERED)
            self.assertEqual(request.offers.get().provider, provider)

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
