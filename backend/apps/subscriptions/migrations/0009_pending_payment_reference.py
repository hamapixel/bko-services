from django.db import migrations, models
from django.db.models import Q


def backfill_paid_pending_references(apps, schema_editor):
    ProviderSubscription = apps.get_model(
        "subscriptions",
        "ProviderSubscription",
    )
    SubscriptionHistory = apps.get_model(
        "subscriptions",
        "SubscriptionHistory",
    )
    PaymentTransaction = apps.get_model(
        "payments",
        "PaymentTransaction",
    )

    subscriptions = ProviderSubscription.objects.exclude(
        pending_plan_id=None,
    ).exclude(
        pending_starts_at=None,
    ).exclude(
        pending_ends_at=None,
    )

    for subscription in subscriptions.iterator():
        payments = PaymentTransaction.objects.filter(
            subscription_id=subscription.pk,
            plan_id=subscription.pending_plan_id,
            status="SUCCEEDED",
            fulfilled_at__isnull=False,
        ).order_by("-fulfilled_at")

        for payment in payments.iterator():
            history_exists = SubscriptionHistory.objects.filter(
                subscription_id=subscription.pk,
                plan_code=payment.plan_code_snapshot,
                starts_at=subscription.pending_starts_at,
                ends_at=subscription.pending_ends_at,
                note__contains=payment.merchant_reference,
            ).exists()
            if history_exists:
                subscription.pending_payment_reference = (
                    payment.merchant_reference
                )
                subscription.save(
                    update_fields=["pending_payment_reference"]
                )
                break


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0002_paymenttransaction_checkout_session_id_and_more"),
        ("subscriptions", "0008_subscriptionhistory_plan_cancel"),
    ]

    operations = [
        migrations.AddField(
            model_name="providersubscription",
            name="pending_payment_reference",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.RunPython(
            backfill_paid_pending_references,
            migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="providersubscription",
            constraint=models.CheckConstraint(
                condition=(
                    Q(pending_plan__isnull=False)
                    | Q(pending_payment_reference="")
                ),
                name="subscriptions_pending_payment_requires_plan",
            ),
        ),
    ]
