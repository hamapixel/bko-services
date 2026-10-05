from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.catalog.models import Category, Trade
from apps.locations.models import City, Commune, Neighborhood, Region

from .models import ProviderProfile, ProviderReview
from .review import review_provider


User = get_user_model()


class ProviderReviewRoleConsistencyTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            phone="+22370002001",
            password="StrongPass123!",
        )
        self.provider_user = User.objects.create_user(
            phone="+22370002002",
            password="StrongPass123!",
            role=User.Role.PROVIDER,
            phone_verified_at=timezone.now(),
        )

        category = Category.objects.create(name="Test bâtiment")
        self.trade = Trade.objects.create(category=category, name="Test plomberie")
        region = Region.objects.create(name="Test région")
        city = City.objects.create(region=region, name="Test ville")
        commune = Commune.objects.create(city=city, name="Test commune")
        self.area = Neighborhood.objects.create(commune=commune, name="Test quartier")

        self.profile = ProviderProfile.objects.create(
            user=self.provider_user,
            legal_name="Prestataire Test",
            display_name="Prestataire Test",
            status=ProviderProfile.Status.VERIFIED,
            is_available=True,
            identity_checked=True,
            review_note="Suspension de test",
            verified_at=timezone.now(),
            verified_by=self.admin,
        )
        self.profile.trades.add(self.trade)
        self.profile.service_areas.add(self.area)

    def test_suspended_provider_keeps_provider_role_through_revalidation(self):
        review_provider(
            self.profile.pk,
            self.admin,
            ProviderReview.Decision.SUSPENDED,
        )
        self.profile.refresh_from_db()
        self.provider_user.refresh_from_db()

        self.assertEqual(self.profile.status, ProviderProfile.Status.SUSPENDED)
        self.assertFalse(self.profile.is_available)
        self.assertEqual(self.provider_user.role, User.Role.PROVIDER)

        self.profile.review_note = "Réouverture du dossier"
        self.profile.save(update_fields=["review_note", "updated_at"])
        review_provider(
            self.profile.pk,
            self.admin,
            ProviderReview.Decision.REOPENED,
        )
        self.profile.refresh_from_db()
        self.provider_user.refresh_from_db()

        self.assertEqual(self.profile.status, ProviderProfile.Status.PENDING)
        self.assertEqual(self.provider_user.role, User.Role.PROVIDER)

        self.profile.review_note = "Nouvelle validation"
        self.profile.identity_checked = True
        self.profile.save(update_fields=["review_note", "identity_checked", "updated_at"])
        review_provider(
            self.profile.pk,
            self.admin,
            ProviderReview.Decision.APPROVED,
        )
        self.profile.refresh_from_db()
        self.provider_user.refresh_from_db()

        self.assertEqual(self.profile.status, ProviderProfile.Status.VERIFIED)
        self.assertEqual(self.provider_user.role, User.Role.PROVIDER)
        self.assertFalse(self.profile.is_available)
