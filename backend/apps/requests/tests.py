from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Category, Trade
from apps.locations.models import City, Commune, Neighborhood

from .models import RequestStatusHistory, ServiceRequest
from .services import create_service_request


class ServiceRequestTests(TestCase):
    def setUp(self):
        self.client_user = get_user_model().objects.create_user(
            phone="+22312345678", password="Strong-password-2026!"
        )
        city = City.objects.get(name="Bamako")
        commune = Commune.objects.create(city=city, name="Commune exemple")
        self.neighborhood = Neighborhood.objects.create(commune=commune, name="Quartier exemple")
        self.category = Category.objects.create(name="Maison")
        self.trade = Trade.objects.create(category=self.category, name="Plomberie")
        self.client = APIClient(enforce_csrf_checks=True)
        self.client.force_login(self.client_user)
        self.token = self.client.get("/api/v1/auth/csrf/").json()["csrfToken"]
        self.payload = {
            "trade": str(self.trade.pk),
            "neighborhood": str(self.neighborhood.pk),
            "title": "Fuite à réparer",
            "description": "Fuite dans la salle de bain",
            "address_detail": "Porte bleue près du marché",
            "priority": "URGENT",
        }

    def create(self, payload=None, csrf=True):
        headers = {"HTTP_X_CSRFTOKEN": self.token} if csrf else {}
        return self.client.post("/api/v1/requests/", payload or self.payload, format="json", **headers)

    def verify_phone(self):
        self.client_user.phone_verified_at = timezone.now()
        self.client_user.save(update_fields=["phone_verified_at"])

    def test_creation_requires_verified_client_and_creates_one_history_entry(self):
        self.assertEqual(self.create(csrf=False).status_code, 403)
        self.assertEqual(self.create().status_code, 403)
        self.verify_phone()
        self.client_user.role = self.client_user.Role.PROVIDER
        self.client_user.save(update_fields=["role"])
        self.assertEqual(self.create().status_code, 403)
        self.client_user.role = self.client_user.Role.CLIENT
        self.client_user.save(update_fields=["role"])
        self.assertEqual(self.create({**self.payload, "client": str(self.client_user.pk)}).status_code, 400)
        self.assertEqual(self.create({**self.payload, "status": "ACCEPTED"}).status_code, 400)
        self.assertEqual(self.create({**self.payload, "price": 100}).status_code, 400)
        self.assertEqual(ServiceRequest.objects.count(), 0)

        response = self.create()
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["priority"], "URGENT")
        self.assertEqual(body["status"], "SEARCHING")
        self.assertEqual(body["status_history"][0]["previous_status"], "")
        self.assertEqual(body["status_history"][0]["new_status"], "CREATED")
        self.assertNotIn("client", body)
        self.assertNotIn("phone", str(body))
        service_request = ServiceRequest.objects.get()
        self.assertEqual(service_request.client, self.client_user)
        self.assertEqual(RequestStatusHistory.objects.count(), 2)
        self.assertEqual(self.client.get("/api/v1/requests/").json()["count"], 1)
        admin_user = get_user_model().objects.create_superuser(
            phone="+22312345670", password="Strong-admin-2026!"
        )
        admin_client = APIClient()
        admin_client.force_login(admin_user)
        self.assertEqual(
            admin_client.get(f"/django-admin/requests/servicerequest/{service_request.pk}/change/").status_code, 200
        )
        self.assertEqual(
            self.client.patch(
                f"/api/v1/requests/{service_request.pk}/", {"status": "ACCEPTED"},
                format="json", HTTP_X_CSRFTOKEN=self.token,
            ).status_code,
            405,
        )

    def test_other_user_cannot_read_request_by_uuid(self):
        self.verify_phone()
        created = self.create().json()
        stranger = get_user_model().objects.create_user(phone="+22312345679", password="Strong-password-2026!")
        other_client = APIClient()
        other_client.force_login(stranger)
        self.assertEqual(other_client.get("/api/v1/requests/").json()["count"], 0)
        self.assertEqual(other_client.get(f"/api/v1/requests/{created['id']}/").status_code, 404)
        self.assertEqual(APIClient().get(f"/api/v1/requests/{created['id']}/").status_code, 403)
        self.assertEqual(self.client.get(f"/api/v1/requests/{created['id']}/").status_code, 200)

    def test_inactive_trade_or_location_is_rejected_without_erasing_existing_request(self):
        self.verify_phone()
        created_id = self.create().json()["id"]
        self.category.is_active = False
        self.category.save(update_fields=["is_active"])
        self.assertEqual(self.create().status_code, 400)
        self.category.is_active = True
        self.category.save(update_fields=["is_active"])
        self.neighborhood.commune.city.is_active = False
        self.neighborhood.commune.city.save(update_fields=["is_active"])
        self.assertEqual(self.create().status_code, 400)
        self.assertEqual(ServiceRequest.objects.count(), 1)
        self.assertEqual(self.client.get(f"/api/v1/requests/{created_id}/").status_code, 200)

    def test_request_and_initial_history_are_atomic(self):
        self.verify_phone()
        with patch("apps.requests.services.RequestStatusHistory.objects.create", side_effect=IntegrityError("history failed")):
            with self.assertRaises(IntegrityError):
                create_service_request(
                    self.client_user.pk,
                    trade=self.trade,
                    neighborhood=self.neighborhood,
                    title="Fuite",
                    description="Fuite à réparer",
                    address_detail="Adresse exemple",
                    priority="NORMAL",
                )
        self.assertEqual(ServiceRequest.objects.count(), 0)
        self.assertEqual(RequestStatusHistory.objects.count(), 0)


    def test_responsive_admin_supervises_request_and_dispatches_matching(self):
        self.verify_phone()
        created = self.create()
        self.assertEqual(created.status_code, 201)
        request_id = created.json()["id"]

        admin_user = get_user_model().objects.create_superuser(
            phone="+22312349999",
            password="Strong-admin-2026!",
        )
        admin = APIClient()
        admin.force_login(admin_user)

        listing = admin.get("/api/v1/admin/requests/?status=SEARCHING&priority=URGENT")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()["count"], 1)
        row = listing.json()["results"][0]
        self.assertEqual(row["id"], request_id)
        self.assertNotIn("address_detail", row)
        self.assertNotIn("description", row)
        self.assertNotIn("client_phone", row)

        detail = admin.get(f"/api/v1/admin/requests/{request_id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["client_phone"], self.client_user.phone)
        self.assertEqual(detail.json()["address_detail"], self.payload["address_detail"])

        dispatched = admin.post(
            f"/api/v1/admin/requests/{request_id}/dispatch/",
            {},
            format="json",
        )
        self.assertEqual(dispatched.status_code, 200)
        self.assertEqual(dispatched.json()["offers_created"], 0)
        self.assertEqual(
            dispatched.json()["request"]["status"],
            ServiceRequest.Status.SEARCHING,
        )

        self.assertEqual(
            admin.get("/api/v1/admin/requests/?status=INVALID").status_code,
            400,
        )
