from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.providers.models import ProviderProfile

from .models import ProviderSubscription, SubscriptionPlan
from .services import apply_paid_subscription, provider_has_entitlement


class SubscriptionPlanChangeTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            phone="+22373110000",
            password="Strong-admin-2026!",
        )
        self.user = User.objects.create_user(
            phone="+22373110001",
            password="Strong-password-2026!",
            role=User.Role.PROVIDER,
            phone_verified_at=timezone.now(),
        )
        self.provider = ProviderProfile.objects.create(
            user=self.user,
            legal_name="Prestataire changement plan",
            display_name="Prestataire changement plan",
            status=ProviderProfile.Status.VERIFIED,
            is_available=True,
            identity_checked=True,
            verified_at=timezone.now(),
            verified_by=self.admin,
        )
        self.essential = SubscriptionPlan.objects.create(
            code="change-essential",
            name="Essentiel test",
            price_xof=2000,
            duration_days=30,
            can_receive_requests=True,
            can_receive_urgent_requests=False,
            max_active_jobs=1,
            is_active=True,
        )
        self.plus = SubscriptionPlan.objects.create(
            code="change-plus",
            name="Plus test",
            price_xof=4000,
            duration_days=30,
            can_receive_requests=True,
            can_receive_urgent_requests=True,
            max_active_jobs=3,
            is_active=True,
        )
        self.pro = SubscriptionPlan.objects.create(
            code="change-pro",
            name="Pro test",
            price_xof=7500,
            duration_days=30,
            can_receive_requests=True,
            can_receive_urgent_requests=True,
            max_active_jobs=None,
            is_active=True,
        )
        self.trial = SubscriptionPlan.objects.create(
            code="change-trial",
            name="Essai test",
            price_xof=0,
            duration_days=14,
            can_receive_requests=True,
            can_receive_urgent_requests=True,
            max_active_jobs=1,
            is_active=True,
        )

    def create_subscription(self, plan, *, days_left=10):
        now = timezone.now()
        return ProviderSubscription.objects.create(
            provider=self.provider,
            plan=plan,
            status=ProviderSubscription.Status.ACTIVE,
            starts_at=now - timedelta(days=5),
            ends_at=now + timedelta(days=days_left),
            activated_by=self.admin,
        )

    def test_paid_upgrade_applies_immediately_and_preserves_remaining_value(self):
        subscription = self.create_subscription(self.essential)
        old_end = subscription.ends_at
        before = timezone.now()

        apply_paid_subscription(
            self.provider.pk,
            plan_id=self.plus.pk,
            duration_days=30,
            payment_reference="BKO-UPGRADE-TEST",
        )

        subscription.refresh_from_db()
        remaining_seconds = max(
            0,
            int((old_end - subscription.starts_at).total_seconds()),
        )
        credit_seconds = (
            remaining_seconds
            * self.essential.price_xof
            // self.plus.price_xof
        )
        expected_end = subscription.starts_at + timedelta(
            days=30,
            seconds=credit_seconds,
        )

        self.assertEqual(subscription.plan, self.plus)
        self.assertIsNone(subscription.pending_plan_id)
        self.assertGreaterEqual(subscription.starts_at, before)
        self.assertEqual(subscription.ends_at, expected_end)
        self.assertTrue(provider_has_entitlement(self.provider.pk, urgent=True))
        history = subscription.history.get()
        self.assertEqual(history.plan_code, self.plus.code)
        self.assertEqual(history.ends_at, subscription.ends_at)

    def test_trial_to_paid_plan_is_an_immediate_upgrade(self):
        subscription = self.create_subscription(self.trial)
        old_end = subscription.ends_at

        apply_paid_subscription(
            self.provider.pk,
            plan_id=self.essential.pk,
            duration_days=30,
            payment_reference="BKO-TRIAL-TO-PAID",
        )

        subscription.refresh_from_db()
        self.assertEqual(subscription.plan, self.essential)
        self.assertIsNone(subscription.pending_plan_id)
        self.assertEqual(subscription.ends_at, old_end + timedelta(days=30))

    def test_paid_downgrade_waits_until_current_period_ends(self):
        subscription = self.create_subscription(self.pro)
        old_end = subscription.ends_at

        apply_paid_subscription(
            self.provider.pk,
            plan_id=self.essential.pk,
            duration_days=30,
            payment_reference="BKO-DOWNGRADE-TEST",
        )

        subscription.refresh_from_db()
        self.assertEqual(subscription.plan, self.pro)
        self.assertEqual(subscription.ends_at, old_end)
        self.assertEqual(subscription.pending_plan, self.essential)
        self.assertEqual(subscription.pending_starts_at, old_end)
        self.assertEqual(
            subscription.pending_ends_at,
            old_end + timedelta(days=30),
        )

        self.assertTrue(
            provider_has_entitlement(
                self.provider.pk,
                urgent=True,
                at=old_end - timedelta(seconds=1),
            )
        )
        self.assertTrue(
            provider_has_entitlement(
                self.provider.pk,
                urgent=False,
                at=old_end + timedelta(seconds=1),
            )
        )
        self.assertFalse(
            provider_has_entitlement(
                self.provider.pk,
                urgent=True,
                at=old_end + timedelta(seconds=1),
            )
        )
        history = subscription.history.get()
        self.assertEqual(history.plan_code, self.essential.code)
        self.assertEqual(history.starts_at, old_end)
        self.assertEqual(history.ends_at, old_end + timedelta(days=30))
        self.assertIn("programmé", history.note)

    def test_same_plan_payment_renews_without_scheduling(self):
        subscription = self.create_subscription(self.plus)
        old_end = subscription.ends_at

        apply_paid_subscription(
            self.provider.pk,
            plan_id=self.plus.pk,
            duration_days=30,
            payment_reference="BKO-RENEW-TEST",
        )

        subscription.refresh_from_db()
        self.assertEqual(subscription.plan, self.plus)
        self.assertIsNone(subscription.pending_plan_id)
        self.assertEqual(subscription.ends_at, old_end + timedelta(days=30))

    def test_new_change_is_rejected_while_downgrade_is_pending(self):
        self.create_subscription(self.pro)
        apply_paid_subscription(
            self.provider.pk,
            plan_id=self.essential.pk,
            duration_days=30,
            payment_reference="BKO-DOWNGRADE-FIRST",
        )

        with self.assertRaises(ValidationError):
            apply_paid_subscription(
                self.provider.pk,
                plan_id=self.plus.pk,
                duration_days=30,
                payment_reference="BKO-SECOND-CHANGE",
            )
