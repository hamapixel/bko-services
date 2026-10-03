import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("subscriptions", "0005_seed_paid_subscription_plans"),
    ]

    operations = [
        migrations.AddField(
            model_name="providersubscription",
            name="pending_plan",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="pending_subscriptions",
                to="subscriptions.subscriptionplan",
            ),
        ),
        migrations.AddField(
            model_name="providersubscription",
            name="pending_starts_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="providersubscription",
            name="pending_ends_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name="providersubscription",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(
                        pending_plan__isnull=True,
                        pending_starts_at__isnull=True,
                        pending_ends_at__isnull=True,
                    )
                    | models.Q(
                        pending_plan__isnull=False,
                        pending_starts_at__isnull=False,
                        pending_ends_at__isnull=False,
                    )
                ),
                name="subscriptions_pending_plan_complete",
            ),
        ),
    ]
