from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Category, Trade
from apps.locations.models import City, Commune, Neighborhood
from apps.providers.models import ProviderProfile
from apps.requests.models import RequestStatusHistory, ServiceRequest

from .models import Review


class ReviewTests(TestCase):
    def setUp(self):
        self.client_user = get_user_model().objects.create_user(
            phone="+22350000000",
            password="Strong-password-2026!",
            phone_verified_at=timezone.now(),
        )
        self.other_client = get_user_model().objects.create_user(
            phone="+22350000001",
            password="Strong-password-2026!",
            phone_verified_at=timezone.now(),
        )
        provider_user = get_user_model().objects.create_user(
            phone="+22350000010",
            password="Strong-password-2026!",
            role="PROVIDER",
            phone_verified_at=timezone.now(),
        )
        self.provider = ProviderProfile.objects.create(
            user=provider_user,
            legal_name="Prestataire avis",
            display_name="Prestataire avis",
            status=ProviderProfile.Status.VERIFIED,
            is_available=True,
            verified_at=timezone.now(),
        )

        city = City.objects.get(name="Bamako")
        commune = Commune.objects.create(city=city, name="Commune avis")
        area = Neighborhood.objects.create(commune=commune, name="Quartier avis")
        trade = Trade.objects.create(
            category=Category.objects.create(name="Catégorie avis"),
            name="Métier avis",
        )
        self.provider.trades.add(trade)
        self.provider.service_areas.add(area)

        self.service_request = ServiceRequest.objects.create(
            client=self.client_user,
            trade=trade,
            neighborhood=area,
            assigned_provider=self.provider,
            title="Intervention terminée",
            description="Intervention terminée et confirmée.",
            address_detail="Adresse privée",
            status=ServiceRequest.Status.CLIENT_CONFIRMED,
        )
        RequestStatusHistory.objects.create(
            service_request=self.service_request,
            actor=self.client_user,
            previous_status=ServiceRequest.Status.PROVIDER_COMPLETED,
            new_status=ServiceRequest.Status.CLIENT_CONFIRMED,
        )

    def test_client_can_create_one_review_after_confirmation(self):
        api = APIClient()
        api.force_login(self.client_user)

        response = api.post(
            f"/api/v1/requests/{self.service_request.pk}/review/",
            {"rating": 5, "comment": "Très bon service."},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["rating"], 5)
        self.assertEqual(response.json()["provider_id"], str(self.provider.pk))
        self.assertNotIn("client", response.json())
        review = Review.objects.get()
        self.assertEqual(review.client, self.client_user)
        self.assertEqual(review.provider, self.provider)
        self.assertEqual(review.service_request, self.service_request)

        duplicate = api.post(
            f"/api/v1/requests/{self.service_request.pk}/review/",
            {"rating": 4, "comment": "Deuxième avis"},
            format="json",
        )
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(Review.objects.count(), 1)

    def test_client_cannot_choose_another_provider(self):
        api = APIClient()
        api.force_login(self.client_user)

        response = api.post(
            f"/api/v1/requests/{self.service_request.pk}/review/",
            {
                "rating": 5,
                "comment": "Tentative de champ interdit",
                "provider_id": str(self.provider.pk),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Review.objects.count(), 0)

    def test_review_requires_client_confirmed_status(self):
        self.service_request.status = ServiceRequest.Status.PROVIDER_COMPLETED
        self.service_request.save(update_fields=["status"])

        api = APIClient()
        api.force_login(self.client_user)
        response = api.post(
            f"/api/v1/requests/{self.service_request.pk}/review/",
            {"rating": 5},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Review.objects.count(), 0)

    def test_other_client_cannot_review_foreign_request(self):
        api = APIClient()
        api.force_login(self.other_client)

        response = api.post(
            f"/api/v1/requests/{self.service_request.pk}/review/",
            {"rating": 5},
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(Review.objects.count(), 0)

    def test_provider_cannot_review_its_intervention(self):
        api = APIClient()
        api.force_login(self.provider.user)

        response = api.post(
            f"/api/v1/requests/{self.service_request.pk}/review/",
            {"rating": 5},
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(Review.objects.count(), 0)

    def test_rating_must_be_between_one_and_five(self):
        api = APIClient()
        api.force_login(self.client_user)

        self.assertEqual(
            api.post(
                f"/api/v1/requests/{self.service_request.pk}/review/",
                {"rating": 0},
                format="json",
            ).status_code,
            400,
        )
        self.assertEqual(
            api.post(
                f"/api/v1/requests/{self.service_request.pk}/review/",
                {"rating": 6},
                format="json",
            ).status_code,
            400,
        )
        self.assertEqual(Review.objects.count(), 0)

    def test_database_enforces_one_review_per_request(self):
        Review.objects.create(
            service_request=self.service_request,
            client=self.client_user,
            provider=self.provider,
            rating=5,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Review.objects.create(
                    service_request=self.service_request,
                    client=self.client_user,
                    provider=self.provider,
                    rating=4,
                )

    def test_public_reviews_expose_no_client_private_data(self):
        Review.objects.create(
            service_request=self.service_request,
            client=self.client_user,
            provider=self.provider,
            rating=5,
            comment="Ponctuel et professionnel.",
        )

        response = APIClient().get(f"/api/v1/providers/{self.provider.pk}/reviews/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        review = response.json()["results"][0]
        self.assertEqual(review["rating"], 5)
        self.assertNotIn("client", review)
        self.assertNotIn("phone", str(review))
