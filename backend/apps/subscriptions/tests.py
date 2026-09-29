from datetime import timedelta
from importlib import import_module

from django.apps import apps as django_apps
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

from .models import ProviderSubscription, SubscriptionHistory, SubscriptionPlan
from .services import provider_has_entitlement


class SubscriptionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            phone="+22373000000",
            password="Strong-admin-2026!",
        )
        self.staff_without_permission = User.objects.create_user(
            phone="+22373000001",
            password="Strong-admin-2026!",
            role=User.Role.ADMIN,
            is_staff=True,
            phone_verified_at=timezone.now(),
        )
        self.client_user = User.objects.create_user(
            phone="+22373000002",
            password="Strong-password-2026!",
            phone_verified_at=timezone.now(),
        )

        city = City.objects.get(name="Bamako")
        commune = Commune.objects.create(city=city, name="Commune abonnements")
        self.area = Neighborhood.objects.create(
            commune=commune,
            name="Quartier abonnements",
        )
        self.trade = Trade.objects.create(
            category=Category.objects.create(name="Catégorie abonnements"),
            name="Métier abonnements",
        )

        self.normal_plan = SubscriptionPlan.objects.create(
            code="normal",
            name="Normal",
            description="Demandes normales uniquement",
            price_xof=5000,
            duration_days=30,
            can_receive_requests=True,
            can_receive_urgent_requests=False,
            display_order=1,
        )
        self.urgent_plan = SubscriptionPlan.objects.create(
            code="urgent",
            name="Urgent",
            description="Demandes normales et urgentes",
            price_xof=10000,
            duration_days=30,
            can_receive_requests=True,
            can_receive_urgent_requests=True,
            display_order=2,
        )
        self.inactive_plan = SubscriptionPlan.objects.create(
            code="old",
            name="Ancien",
            price_xof=1000,
            duration_days=30,
            can_receive_requests=True,
            can_receive_urgent_requests=True,
            is_active=False,
            display_order=3,
        )

        self.provider = self.create_provider(
            "+22373000010",
            "Prestataire principal",
        )
        self.other_provider = self.create_provider(
            "+22373000011",
            "Prestataire secondaire",
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

    def create_subscription(self, provider, plan=None, *, starts_at=None, ends_at=None):
        now = timezone.now()
        return ProviderSubscription.objects.create(
            provider=provider,
            plan=plan or self.urgent_plan,
            starts_at=starts_at or now - timedelta(minutes=1),
            ends_at=ends_at or now + timedelta(days=30),
            activated_by=self.admin,
        )

    def create_request(self, priority=ServiceRequest.Priority.NORMAL):
        return create_service_request(
            self.client_user.pk,
            trade=self.trade,
            neighborhood=self.area,
            title="Demande avec abonnement",
            description="Description privée.",
            address_detail="Adresse privée.",
            priority=priority,
        )

    def test_public_endpoint_lists_only_active_plans(self):
        response = APIClient().get("/api/v1/subscriptions/plans/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 2)
        codes = [item["code"] for item in response.json()["results"]]
        self.assertEqual(codes, ["normal", "urgent"])
        self.assertNotIn("is_active", response.json()["results"][0])

    def test_admin_can_prepare_monthly_plan_but_must_set_price_before_publication(self):
        admin = APIClient()
        admin.force_login(self.admin)
        response = admin.post(
            "/api/v1/subscriptions/admin/plans/",
            {
                "code": "mensuel-essentiel", "name": "Mensuel Essentiel",
                "price_xof": 0, "duration_days": 30, "is_active": False,
                "max_active_jobs": 1,
                "can_receive_requests": True, "can_receive_urgent_requests": False,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        plan_id = response.json()["id"]
        path = f"/api/v1/subscriptions/admin/plans/{plan_id}/"
        self.assertEqual(
            admin.patch(path, {"is_active": True}, format="json").status_code, 400
        )
        updated = admin.patch(
            path, {"price_xof": 5000, "is_active": True}, format="json"
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["duration_days"], 30)
        self.assertEqual(updated.json()["max_active_jobs"], 1)
        public_codes = [item["code"] for item in APIClient().get(
            "/api/v1/subscriptions/plans/"
        ).json()["results"]]
        self.assertIn("mensuel-essentiel", public_codes)

    def test_provider_sees_only_own_subscription(self):
        self.create_subscription(self.provider)

        own = APIClient()
        own.force_login(self.provider.user)
        response = own.get("/api/v1/subscriptions/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["subscription"]["plan"]["code"], "urgent")

        other = APIClient()
        other.force_login(self.other_provider.user)
        other_response = other.get("/api/v1/subscriptions/me/")
        self.assertEqual(other_response.status_code, 200)
        self.assertIsNone(other_response.json()["subscription"])

        client = APIClient()
        client.force_login(self.client_user)
        self.assertEqual(client.get("/api/v1/subscriptions/me/").status_code, 403)

    def test_only_authorized_admin_can_manage_plans_and_subscriptions(self):
        denied = APIClient()
        denied.force_login(self.staff_without_permission)
        self.assertEqual(
            denied.get("/api/v1/subscriptions/admin/plans/").status_code,
            403,
        )
        self.assertEqual(
            denied.post(
                f"/api/v1/subscriptions/admin/providers/{self.provider.pk}/activate/",
                {"plan_id": str(self.normal_plan.pk)},
                format="json",
            ).status_code,
            403,
        )
        self.assertEqual(
            denied.get("/api/v1/subscriptions/admin/providers/").status_code,
            403,
        )

        allowed = APIClient()
        allowed.force_login(self.admin)
        self.assertEqual(
            allowed.get("/api/v1/subscriptions/admin/plans/").status_code,
            200,
        )
        providers = allowed.get("/api/v1/subscriptions/admin/providers/")
        self.assertEqual(providers.status_code, 200)
        self.assertEqual(providers.json()["count"], 2)
        self.assertFalse(providers.json()["results"][0]["has_subscription"])

    def test_admin_activation_creates_period_and_history(self):
        api = APIClient()
        api.force_login(self.admin)

        response = api.post(
            f"/api/v1/subscriptions/admin/providers/{self.provider.pk}/activate/",
            {
                "plan_id": str(self.normal_plan.pk),
                "note": "Activation manuelle de test.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        subscription = ProviderSubscription.objects.get(provider=self.provider)
        self.assertEqual(subscription.plan, self.normal_plan)
        self.assertEqual(subscription.status, ProviderSubscription.Status.ACTIVE)
        self.assertGreater(subscription.ends_at, subscription.starts_at)
        self.assertEqual(subscription.history.count(), 1)
        history = subscription.history.get()
        self.assertEqual(history.action, SubscriptionHistory.Action.ACTIVATED)
        self.assertEqual(history.plan_code, "normal")
        self.assertEqual(history.note, "Activation manuelle de test.")
        self.assertTrue(provider_has_entitlement(self.provider.pk))
        self.assertFalse(provider_has_entitlement(self.provider.pk, urgent=True))

        duplicate = api.post(
            f"/api/v1/subscriptions/admin/providers/{self.provider.pk}/activate/",
            {"plan_id": str(self.urgent_plan.pk)},
            format="json",
        )
        self.assertEqual(duplicate.status_code, 400)

    def test_renewal_extends_period_and_can_change_plan(self):
        subscription = self.create_subscription(self.provider, self.normal_plan)
        old_end = subscription.ends_at

        api = APIClient()
        api.force_login(self.admin)
        response = api.post(
            f"/api/v1/subscriptions/admin/subscriptions/{subscription.pk}/renew/",
            {
                "plan_id": str(self.urgent_plan.pk),
                "note": "Passage au plan urgent.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        subscription.refresh_from_db()
        self.assertEqual(subscription.plan, self.urgent_plan)
        self.assertEqual(subscription.ends_at, old_end + timedelta(days=30))
        self.assertTrue(provider_has_entitlement(self.provider.pk, urgent=True))
        history = subscription.history.get()
        self.assertEqual(history.action, SubscriptionHistory.Action.RENEWED)
        self.assertEqual(history.plan_code, "urgent")

    def test_free_trial_is_once_only_and_paid_plan_restores_offers(self):
        trial = SubscriptionPlan.objects.create(
            code="essai-14j", name="Essai 14 jours", price_xof=0,
            duration_days=14, can_receive_requests=True,
            can_receive_urgent_requests=True, max_active_jobs=1,
        )
        another_trial = SubscriptionPlan.objects.create(
            code="autre-essai", name="Autre essai", price_xof=0,
            duration_days=7, can_receive_requests=True,
        )
        admin = APIClient()
        admin.force_login(self.admin)
        activation_url = f"/api/v1/subscriptions/admin/providers/{self.provider.pk}/activate/"
        self.assertEqual(
            admin.post(activation_url, {"plan_id": str(trial.pk)}, format="json").status_code,
            201,
        )
        subscription = ProviderSubscription.objects.get(provider=self.provider)
        self.assertIsNotNone(subscription.free_trial_used_at)
        subscription.ends_at = timezone.now() - timedelta(seconds=1)
        subscription.save(update_fields=["ends_at"])

        provider_api = APIClient()
        provider_api.force_login(self.provider.user)
        status = provider_api.get("/api/v1/subscriptions/me/")
        self.assertEqual(status.json()["subscription"]["status"], "EXPIRED")
        self.assertIsNotNone(status.json()["subscription"]["free_trial_used_at"])
        self.assertFalse(provider_has_entitlement(self.provider.pk))
        request = self.create_request()
        self.assertFalse(ServiceOffer.objects.filter(service_request=request).exists())

        renew_url = f"/api/v1/subscriptions/admin/subscriptions/{subscription.pk}/renew/"
        self.assertEqual(admin.post(renew_url, {}, format="json").status_code, 400)
        self.assertEqual(
            admin.post(renew_url, {"plan_id": str(another_trial.pk)}, format="json").status_code,
            400,
        )
        self.assertEqual(
            admin.post(activation_url, {"plan_id": str(another_trial.pk)}, format="json").status_code,
            400,
        )
        subscription.refresh_from_db()
        self.assertEqual(subscription.plan, trial)
        self.assertEqual(subscription.history.count(), 1)
        self.assertFalse(provider_has_entitlement(self.provider.pk))

        self.assertEqual(
            admin.post(activation_url, {"plan_id": str(self.normal_plan.pk)}, format="json").status_code,
            201,
        )
        subscription.refresh_from_db()
        self.assertEqual(subscription.plan, self.normal_plan)
        self.assertIsNotNone(subscription.free_trial_used_at)
        self.assertTrue(provider_has_entitlement(self.provider.pk))
        self.assertEqual(
            admin.post(activation_url, {"plan_id": str(trial.pk)}, format="json").status_code,
            400,
        )

    def test_migration_marks_legacy_trial_even_after_paid_plan(self):
        subscription = self.create_subscription(self.provider, self.normal_plan)
        prior_trial = timezone.now() - timedelta(days=8)
        SubscriptionHistory.objects.create(
            subscription=subscription,
            actor=self.admin,
            action=SubscriptionHistory.Action.ACTIVATED,
            plan_code="essai-7j",
            plan_name="Essai 7 jours",
            starts_at=prior_trial,
            ends_at=prior_trial + timedelta(days=7),
        )
        migration = import_module("apps.subscriptions.migrations.0004_free_trial_used_at")
        migration.mark_previous_trials(django_apps, None)
        subscription.refresh_from_db()
        self.assertIsNotNone(subscription.free_trial_used_at)

        subscription.status = ProviderSubscription.Status.CANCELLED
        subscription.save(update_fields=["status"])
        trial = SubscriptionPlan.objects.create(
            code="essai-14j", name="Essai 14 jours", price_xof=0,
            duration_days=14, can_receive_requests=True,
        )
        admin = APIClient()
        admin.force_login(self.admin)
        self.assertEqual(
            admin.post(
                f"/api/v1/subscriptions/admin/providers/{self.provider.pk}/activate/",
                {"plan_id": str(trial.pk)}, format="json",
            ).status_code,
            400,
        )

    def test_cancelled_subscription_loses_entitlement_and_is_audited(self):
        subscription = self.create_subscription(self.provider)

        api = APIClient()
        api.force_login(self.admin)
        response = api.post(
            f"/api/v1/subscriptions/admin/subscriptions/{subscription.pk}/cancel/",
            {"note": "Annulation administrative."},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, ProviderSubscription.Status.CANCELLED)
        self.assertIsNotNone(subscription.cancelled_at)
        self.assertFalse(provider_has_entitlement(self.provider.pk))
        self.assertEqual(
            subscription.history.get().action,
            SubscriptionHistory.Action.CANCELLED,
        )

    def test_expired_subscription_is_reported_expired_and_has_no_entitlement(self):
        now = timezone.now()
        self.create_subscription(
            self.provider,
            starts_at=now - timedelta(days=31),
            ends_at=now - timedelta(minutes=1),
        )

        api = APIClient()
        api.force_login(self.provider.user)
        response = api.get("/api/v1/subscriptions/me/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["subscription"]["status"],
            ProviderSubscription.Status.EXPIRED,
        )
        self.assertFalse(provider_has_entitlement(self.provider.pk))

    def test_normal_plan_receives_normal_request_but_not_urgent_request(self):
        self.create_subscription(self.provider, self.normal_plan)

        normal = self.create_request(ServiceRequest.Priority.NORMAL)
        self.assertEqual(ServiceOffer.objects.filter(service_request=normal).count(), 1)
        self.assertEqual(
            ServiceOffer.objects.get(service_request=normal).provider,
            self.provider,
        )

        urgent = self.create_request(ServiceRequest.Priority.URGENT)
        self.assertEqual(dispatch_request(urgent.pk, self.admin), 0)
        self.assertFalse(ServiceOffer.objects.filter(service_request=urgent).exists())

    def test_urgent_matching_excludes_unsubscribed_provider(self):
        self.create_subscription(self.provider, self.urgent_plan)

        urgent = self.create_request(ServiceRequest.Priority.URGENT)
        self.assertEqual(ServiceOffer.objects.filter(service_request=urgent).count(), 1)
        offer = ServiceOffer.objects.get(service_request=urgent)
        self.assertEqual(offer.provider, self.provider)
        self.assertNotEqual(offer.provider, self.other_provider)

    def test_acceptance_revalidates_subscription_expiration(self):
        subscription = self.create_subscription(self.provider, self.urgent_plan)
        urgent = self.create_request(ServiceRequest.Priority.URGENT)
        self.assertEqual(ServiceOffer.objects.filter(service_request=urgent).count(), 1)
        offer = ServiceOffer.objects.get(service_request=urgent)

        subscription.ends_at = timezone.now() - timedelta(seconds=1)
        subscription.save(update_fields=["ends_at"])

        api = APIClient()
        api.force_login(self.provider.user)
        response = api.post(
            f"/api/v1/providers/offers/{offer.pk}/accept/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        urgent.refresh_from_db()
        offer.refresh_from_db()
        self.assertEqual(urgent.status, ServiceRequest.Status.OFFERED)
        self.assertIsNone(urgent.assigned_provider)
        self.assertEqual(offer.status, ServiceOffer.Status.PENDING)

    def test_plan_validation_rejects_invalid_rights_duration_and_extra_fields(self):
        api = APIClient()
        api.force_login(self.admin)

        invalid_rights = api.post(
            "/api/v1/subscriptions/admin/plans/",
            {
                "code": "invalid-rights",
                "name": "Invalid",
                "price_xof": 1000,
                "duration_days": 30,
                "can_receive_requests": False,
                "can_receive_urgent_requests": True,
                "is_active": True,
                "display_order": 10,
            },
            format="json",
        )
        self.assertEqual(invalid_rights.status_code, 400)

        invalid_duration = api.post(
            "/api/v1/subscriptions/admin/plans/",
            {
                "code": "invalid-duration",
                "name": "Invalid duration",
                "price_xof": 1000,
                "duration_days": 0,
                "can_receive_requests": True,
                "can_receive_urgent_requests": False,
                "is_active": True,
                "display_order": 10,
            },
            format="json",
        )
        self.assertEqual(invalid_duration.status_code, 400)

        extra_field = api.post(
            "/api/v1/subscriptions/admin/plans/",
            {
                "code": "malicious",
                "name": "Malicious",
                "price_xof": 1000,
                "duration_days": 30,
                "can_receive_requests": True,
                "can_receive_urgent_requests": False,
                "is_active": True,
                "display_order": 10,
                "owner_id": str(self.client_user.pk),
            },
            format="json",
        )
        self.assertEqual(extra_field.status_code, 400)

    def test_inactive_plan_cannot_be_activated(self):
        api = APIClient()
        api.force_login(self.admin)

        response = api.post(
            f"/api/v1/subscriptions/admin/providers/{self.provider.pk}/activate/",
            {"plan_id": str(self.inactive_plan.pk)},
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(
            ProviderSubscription.objects.filter(provider=self.provider).exists()
        )
