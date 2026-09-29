from django.db import migrations, models


def mark_previous_trials(apps, schema_editor):
    Plan = apps.get_model("subscriptions", "SubscriptionPlan")
    Subscription = apps.get_model("subscriptions", "ProviderSubscription")
    History = apps.get_model("subscriptions", "SubscriptionHistory")

    free_plan_ids = set(Plan.objects.filter(price_xof=0).values_list("pk", flat=True))
    free_codes = set(Plan.objects.filter(price_xof=0).values_list("code", flat=True))
    free_codes.update(("essai-7j", "essai-14j"))

    for subscription in Subscription.objects.all().iterator():
        first_trial = (
            History.objects.filter(
                subscription_id=subscription.pk,
                plan_code__in=free_codes,
                action__in=("ACTIVATED", "RENEWED"),
            )
            .order_by("created_at")
            .first()
        )
        used_at = first_trial.created_at if first_trial else (
            subscription.starts_at if subscription.plan_id in free_plan_ids else None
        )
        if used_at is not None:
            Subscription.objects.filter(pk=subscription.pk).update(free_trial_used_at=used_at)


class Migration(migrations.Migration):
    dependencies = [("subscriptions", "0003_limit_existing_trial")]

    operations = [
        migrations.AddField(
            model_name="providersubscription",
            name="free_trial_used_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(mark_previous_trials, migrations.RunPython.noop),
    ]
