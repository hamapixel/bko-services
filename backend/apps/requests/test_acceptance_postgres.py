import threading
from datetime import timedelta
from queue import Queue
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection, connections
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.catalog.models import Category, Trade
from apps.locations.models import City, Commune, Neighborhood
from apps.providers.models import ProviderProfile
from apps.subscriptions.models import ProviderSubscription, SubscriptionPlan

from .acceptance import accept_offer
from .matching import dispatch_request
from .models import ServiceOffer, ServiceRequest
from .services import create_service_request
from .workflow import confirm_client_completion, transition_provider_intervention


@skipUnless(connection.vendor == "postgresql", "Ce test de concurrence nécessite PostgreSQL.")
class AcceptanceConcurrencyPostgresTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.client_user = get_user_model().objects.create_user(
            phone="+22330000000",
            password="Strong-password-2026!",
            phone_verified_at=timezone.now(),
        )
        self.admin_user = get_user_model().objects.create_superuser(
            phone="+22330000001",
            password="Strong-admin-2026!",
        )
        city = City.objects.get(name="Bamako")
        commune = Commune.objects.create(city=city, name="Commune concurrence")
        self.area = Neighborhood.objects.create(commune=commune, name="Quartier concurrence")
        self.trade = Trade.objects.create(
            category=Category.objects.create(name="Urgence"),
            name="Plomberie urgence",
        )
        self.plan = SubscriptionPlan.objects.create(
            code="concurrency-test",
            name="Concurrency Test",
            price_xof=0,
            duration_days=30,
            can_receive_requests=True,
            can_receive_urgent_requests=True,
        )

    def create_provider(self, phone):
        user = get_user_model().objects.create_user(
            phone=phone,
            password="Strong-password-2026!",
            role="PROVIDER",
            phone_verified_at=timezone.now(),
        )
        profile = ProviderProfile.objects.create(
            user=user,
            legal_name="Nom privé",
            display_name=phone,
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

    def test_only_one_provider_wins_when_two_accept_together(self):
        providers = [
            self.create_provider("+22330000010"),
            self.create_provider("+22330000011"),
        ]
        service_request = create_service_request(
            self.client_user.pk,
            trade=self.trade,
            neighborhood=self.area,
            title="Urgence",
            description="Détails privés",
            address_detail="Adresse privée",
            priority=ServiceRequest.Priority.URGENT,
        )
        self.assertEqual(ServiceOffer.objects.filter(service_request=service_request).count(), 2)
        offers = list(ServiceOffer.objects.filter(service_request=service_request).order_by("created_at", "id"))

        barrier = threading.Barrier(2)
        results = Queue()

        def worker(user_id, offer_id):
            close_old_connections()
            try:
                user = get_user_model().objects.get(pk=user_id)
                barrier.wait(timeout=10)
                try:
                    accept_offer(offer_id, user)
                    results.put("accepted")
                except ValidationError:
                    results.put("rejected")
            finally:
                connections["default"].close()

        threads = [
            threading.Thread(target=worker, args=(providers[0].user_id, offers[0].pk)),
            threading.Thread(target=worker, args=(providers[1].user_id, offers[1].pk)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)

        self.assertFalse(any(thread.is_alive() for thread in threads))
        outcomes = sorted([results.get_nowait(), results.get_nowait()])
        self.assertEqual(outcomes, ["accepted", "rejected"])

        service_request.refresh_from_db()
        self.assertEqual(service_request.status, ServiceRequest.Status.ACCEPTED)
        self.assertIsNotNone(service_request.assigned_provider_id)
        self.assertEqual(
            ServiceOffer.objects.filter(
                service_request=service_request,
                status=ServiceOffer.Status.ACCEPTED,
            ).count(),
            1,
        )

    def test_assigned_provider_can_advance_and_client_can_confirm(self):
        provider = self.create_provider("+22330000012")
        service_request = create_service_request(
            self.client_user.pk,
            trade=self.trade,
            neighborhood=self.area,
            title="Fuite urgente",
            description="Détails privés",
            address_detail="Adresse privée",
            priority=ServiceRequest.Priority.URGENT,
        )
        offer = ServiceOffer.objects.get(service_request=service_request, provider=provider)
        accept_offer(offer.pk, provider.user)

        for target in (
            ServiceRequest.Status.EN_ROUTE,
            ServiceRequest.Status.ARRIVED,
            ServiceRequest.Status.IN_PROGRESS,
            ServiceRequest.Status.PROVIDER_COMPLETED,
        ):
            transition_provider_intervention(service_request.pk, provider.user, target)
        confirm_client_completion(service_request.pk, self.client_user)

        service_request.refresh_from_db()
        self.assertEqual(service_request.status, ServiceRequest.Status.CLIENT_CONFIRMED)
