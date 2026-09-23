from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Category, Trade
from apps.locations.models import City, Commune, Neighborhood
from apps.providers.models import ProviderProfile
from apps.requests.acceptance import accept_offer
from apps.requests.matching import dispatch_request
from apps.requests.models import ServiceOffer, ServiceRequest
from apps.requests.services import create_service_request
from apps.requests.workflow import confirm_client_completion, transition_provider_intervention
from apps.reviews.services import create_review

from .models import Notification
from .services import create_notification


class NotificationCenterTests(TestCase):
    def setUp(self):
        self.client_user = get_user_model().objects.create_user(
            phone="+22360000000",
            password="Strong-password-2026!",
            phone_verified_at=timezone.now(),
        )
        self.admin_user = get_user_model().objects.create_superuser(
            phone="+22360000001",
            password="Strong-admin-2026!",
        )

        city = City.objects.get(name="Bamako")
        commune = Commune.objects.create(city=city, name="Commune notifications")
        self.area = Neighborhood.objects.create(commune=commune, name="Quartier notifications")
        self.trade = Trade.objects.create(
            category=Category.objects.create(name="Catégorie notifications"),
            name="Métier notifications",
        )

        self.provider1 = self.create_provider("+22360000010", "Prestataire 1")
        self.provider2 = self.create_provider("+22360000011", "Prestataire 2")

        self.service_request = create_service_request(
            self.client_user.pk,
            trade=self.trade,
            neighborhood=self.area,
            title="Demande notifications",
            description="Description privée",
            address_detail="Adresse privée",
            priority=ServiceRequest.Priority.URGENT,
        )

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
        return profile

    def dispatch_two_offers(self):
        self.assertEqual(dispatch_request(self.service_request.pk, self.admin_user), 2)

    def accept_provider1(self):
        offer = ServiceOffer.objects.get(
            service_request=self.service_request,
            provider=self.provider1,
        )
        accept_offer(offer.pk, self.provider1.user)
        self.service_request.refresh_from_db()

    def test_notifications_are_private_and_can_be_marked_read(self):
        self.dispatch_two_offers()

        own = APIClient()
        own.force_login(self.provider1.user)
        listing = own.get("/api/v1/notifications/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()["count"], 1)
        item = listing.json()["results"][0]
        self.assertEqual(item["kind"], Notification.Kind.OFFER_RECEIVED)
        self.assertFalse(item["is_read"])
        self.assertNotIn("recipient", item)
        self.assertNotIn("phone", str(item))

        self.assertEqual(
            own.get("/api/v1/notifications/unread-count/").json()["unread_count"],
            1,
        )

        foreign = APIClient()
        foreign.force_login(self.provider2.user)
        self.assertEqual(
            foreign.post(f"/api/v1/notifications/{item['id']}/read/").status_code,
            404,
        )

        marked = own.post(f"/api/v1/notifications/{item['id']}/read/")
        self.assertEqual(marked.status_code, 200)
        self.assertTrue(marked.json()["is_read"])
        self.assertEqual(
            own.get("/api/v1/notifications/unread-count/").json()["unread_count"],
            0,
        )

        self.assertEqual(APIClient().get("/api/v1/notifications/").status_code, 403)

    def test_read_all_only_marks_current_users_notifications(self):
        self.dispatch_two_offers()
        create_notification(
            recipient_id=self.provider1.user_id,
            kind=Notification.Kind.CLIENT_CONFIRMED,
            title="Test interne",
            message="Deuxième notification de test.",
            service_request=self.service_request,
        )

        own = APIClient()
        own.force_login(self.provider1.user)
        response = own.post("/api/v1/notifications/read-all/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["marked_read"], 2)
        self.assertEqual(
            Notification.objects.filter(
                recipient=self.provider1.user,
                read_at__isnull=True,
            ).count(),
            0,
        )
        self.assertEqual(
            Notification.objects.filter(
                recipient=self.provider2.user,
                read_at__isnull=True,
            ).count(),
            1,
        )

    def test_complete_business_flow_creates_expected_notifications(self):
        self.dispatch_two_offers()

        self.assertEqual(
            list(
                Notification.objects.filter(recipient=self.provider1.user)
                .values_list("kind", flat=True)
            ),
            [Notification.Kind.OFFER_RECEIVED],
        )
        self.assertEqual(
            list(
                Notification.objects.filter(recipient=self.provider2.user)
                .values_list("kind", flat=True)
            ),
            [Notification.Kind.OFFER_RECEIVED],
        )

        self.accept_provider1()

        self.assertTrue(
            Notification.objects.filter(
                recipient=self.client_user,
                kind=Notification.Kind.REQUEST_ACCEPTED,
                service_request=self.service_request,
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.provider2.user,
                kind=Notification.Kind.OFFER_CANCELLED,
                service_request=self.service_request,
            ).exists()
        )

        for target in (
            ServiceRequest.Status.EN_ROUTE,
            ServiceRequest.Status.ARRIVED,
            ServiceRequest.Status.IN_PROGRESS,
            ServiceRequest.Status.PROVIDER_COMPLETED,
        ):
            transition_provider_intervention(
                self.service_request.pk,
                self.provider1.user,
                target,
            )

        confirm_client_completion(self.service_request.pk, self.client_user)
        create_review(
            self.service_request.pk,
            self.client_user,
            rating=5,
            comment="Très bon service.",
        )

        client_kinds = set(
            Notification.objects.filter(recipient=self.client_user)
            .values_list("kind", flat=True)
        )
        self.assertEqual(
            client_kinds,
            {
                Notification.Kind.REQUEST_ACCEPTED,
                Notification.Kind.PROVIDER_EN_ROUTE,
                Notification.Kind.PROVIDER_ARRIVED,
                Notification.Kind.WORK_STARTED,
                Notification.Kind.PROVIDER_COMPLETED,
            },
        )

        provider1_kinds = set(
            Notification.objects.filter(recipient=self.provider1.user)
            .values_list("kind", flat=True)
        )
        self.assertEqual(
            provider1_kinds,
            {
                Notification.Kind.OFFER_RECEIVED,
                Notification.Kind.CLIENT_CONFIRMED,
                Notification.Kind.REVIEW_RECEIVED,
            },
        )

        provider2_kinds = set(
            Notification.objects.filter(recipient=self.provider2.user)
            .values_list("kind", flat=True)
        )
        self.assertEqual(
            provider2_kinds,
            {
                Notification.Kind.OFFER_RECEIVED,
                Notification.Kind.OFFER_CANCELLED,
            },
        )

    def test_invalid_transition_does_not_create_progress_notification(self):
        self.dispatch_two_offers()
        self.accept_provider1()

        api = APIClient()
        api.force_login(self.provider1.user)
        response = api.post(
            f"/api/v1/providers/interventions/{self.service_request.pk}/transition/",
            {"status": ServiceRequest.Status.ARRIVED},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            Notification.objects.filter(
                recipient=self.client_user,
                kind=Notification.Kind.PROVIDER_ARRIVED,
                service_request=self.service_request,
            ).exists()
        )

    def test_same_request_event_is_idempotent(self):
        first = create_notification(
            recipient_id=self.client_user.pk,
            kind=Notification.Kind.REQUEST_ACCEPTED,
            title="Première version",
            message="Message initial.",
            service_request=self.service_request,
        )
        second = create_notification(
            recipient_id=self.client_user.pk,
            kind=Notification.Kind.REQUEST_ACCEPTED,
            title="Deuxième version",
            message="Ce doublon ne doit pas créer une seconde ligne.",
            service_request=self.service_request,
        )

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(
            Notification.objects.filter(
                recipient=self.client_user,
                service_request=self.service_request,
                kind=Notification.Kind.REQUEST_ACCEPTED,
            ).count(),
            1,
        )

    def test_unread_query_returns_only_unread_notifications(self):
        self.dispatch_two_offers()
        notification = Notification.objects.get(
            recipient=self.provider1.user,
            kind=Notification.Kind.OFFER_RECEIVED,
        )
        own = APIClient()
        own.force_login(self.provider1.user)
        own.post(f"/api/v1/notifications/{notification.pk}/read/")

        create_notification(
            recipient_id=self.provider1.user_id,
            kind=Notification.Kind.CLIENT_CONFIRMED,
            title="Encore non lue",
            message="Notification encore non lue.",
            service_request=self.service_request,
        )

        response = own.get("/api/v1/notifications/?unread=true")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(
            response.json()["results"][0]["kind"],
            Notification.Kind.CLIENT_CONFIRMED,
        )
