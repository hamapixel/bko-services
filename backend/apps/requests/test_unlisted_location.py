from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Category, Trade
from apps.locations.models import City, Commune, Neighborhood, Region
from apps.notifications.models import Notification
from apps.providers.models import ProviderProfile
from apps.subscriptions.models import ProviderSubscription, SubscriptionPlan

from .models import ServiceRequest


class UnlistedLocationTests(TestCase):
    def setUp(self):
        self.region = Region.objects.get(name="Kayes")
        self.trade = Trade.objects.create(category=Category.objects.create(name="Réparations"), name="Plombier")
        self.user = get_user_model().objects.create_user(
            phone="+22370001001", password="Secure-2026-test", phone_verified_at=timezone.now(),
        )
        self.admin = get_user_model().objects.create_superuser(
            phone="+22370001002", password="Secure-2026-test",
        )
        self.client_api = APIClient()
        self.client_api.force_login(self.user)
        self.admin_api = APIClient()
        self.admin_api.force_login(self.admin)
        self.payload = {
            "trade": str(self.trade.pk), "requested_region": str(self.region.pk),
            "requested_city": "Kayes", "requested_commune": "Commune de Kayes",
            "requested_neighborhood": "Quartier indiqué",
            "title": "Fuite d'eau", "description": "Tuyau à réparer",
            "address_detail": "Près du marché", "priority": "NORMAL",
        }

    def test_client_can_submit_unlisted_region_and_admin_must_verify_before_matching(self):
        response = self.client_api.post("/api/v1/requests/", self.payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["status"], ServiceRequest.Status.LOCATION_PENDING)
        self.assertEqual(response.data["region_name"], "Kayes")
        request = ServiceRequest.objects.get(pk=response.data["id"])
        self.assertIsNone(request.neighborhood)
        self.assertEqual(request.offers.count(), 0)
        self.assertTrue(Notification.objects.filter(
            service_request=request, recipient=self.admin,
            kind=Notification.Kind.REQUEST_LOCATION_PENDING, read_at__isnull=True,
        ).exists())
        admin_list = self.admin_api.get("/api/v1/admin/requests/").data["results"][0]
        self.assertEqual(admin_list["neighborhood_name"], "Zone à vérifier")
        self.assertNotIn("requested_city", admin_list)
        self.assertEqual(
            self.admin_api.get(f"/api/v1/admin/requests/{request.pk}/").data["requested_city"],
            "Kayes",
        )
        self.assertEqual(self.admin_api.get("/api/v1/admin/overview/").data["requests_waiting"], 1)
        self.assertEqual(self.admin_api.post(
            f"/api/v1/admin/requests/{request.pk}/dispatch/", {}, format="json",
        ).status_code, 400)

        city = City.objects.create(region=self.region, name="Kayes")
        commune = Commune.objects.create(city=city, name="Commune de Kayes")
        area = Neighborhood.objects.create(commune=commune, name="Quartier indiqué")
        provider_user = get_user_model().objects.create_user(
            phone="+22370001003", password="Secure-2026-test", role="PROVIDER",
            phone_verified_at=timezone.now(),
        )
        provider = ProviderProfile.objects.create(
            user=provider_user, legal_name="Artisan validé", display_name="Artisan",
            status=ProviderProfile.Status.VERIFIED, is_available=True,
            verified_at=timezone.now(),
        )
        provider.trades.add(self.trade)
        provider.service_areas.add(area)
        plan = SubscriptionPlan.objects.create(
            code="region-test", name="Test", price_xof=0, duration_days=30,
            can_receive_requests=True, can_receive_urgent_requests=True,
        )
        ProviderSubscription.objects.create(
            provider=provider, plan=plan, starts_at=timezone.now() - timedelta(minutes=1),
            ends_at=timezone.now() + timedelta(days=30),
        )
        resolved = self.admin_api.post(
            f"/api/v1/admin/requests/{request.pk}/resolve-location/",
            {"neighborhood": str(area.pk)}, format="json",
        )
        self.assertEqual(resolved.status_code, 200, resolved.data)
        request.refresh_from_db()
        self.assertEqual(request.status, ServiceRequest.Status.OFFERED)
        self.assertEqual(request.offers.get().provider, provider)
        self.assertTrue(Notification.objects.filter(
            service_request=request, kind=Notification.Kind.REQUEST_LOCATION_PENDING,
            read_at__isnull=False,
        ).exists())
        self.assertEqual(self.client_api.get(f"/api/v1/requests/{request.pk}/").data["neighborhood_name"], area.name)
        self.assertEqual(self.admin_api.post(
            f"/api/v1/admin/requests/{request.pk}/resolve-location/",
            {"neighborhood": str(area.pk)}, format="json",
        ).status_code, 400)

    def test_rejects_incomplete_input_existing_region_and_cross_region_resolution(self):
        incomplete = dict(self.payload, requested_commune=" ")
        self.assertEqual(self.client_api.post("/api/v1/requests/", incomplete, format="json").status_code, 400)
        bamako_area = Neighborhood.objects.filter(commune__city__name="Bamako").first()
        self.assertEqual(self.client_api.post(
            "/api/v1/requests/", dict(self.payload, requested_region=str(bamako_area.commune.city.region_id)),
            format="json",
        ).status_code, 400)
        response = self.client_api.post("/api/v1/requests/", self.payload, format="json")
        request_id = response.data["id"]
        self.assertEqual(self.client_api.post(
            f"/api/v1/admin/requests/{request_id}/resolve-location/",
            {"neighborhood": str(bamako_area.pk)}, format="json",
        ).status_code, 403)
        self.assertEqual(self.admin_api.post(
            f"/api/v1/admin/requests/{request_id}/resolve-location/",
            {"neighborhood": str(bamako_area.pk)}, format="json",
        ).status_code, 400)
        self.assertEqual(ServiceRequest.objects.get(pk=request_id).status, ServiceRequest.Status.LOCATION_PENDING)
