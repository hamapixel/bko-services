from django.db import migrations


def limit_existing_trial(apps, schema_editor):
    plan = apps.get_model("subscriptions", "SubscriptionPlan")
    plan.objects.filter(
        code="essai-14j", price_xof=0, duration_days=14, max_active_jobs__isnull=True
    ).update(max_active_jobs=1)


class Migration(migrations.Migration):
    dependencies = [("subscriptions", "0002_subscriptionplan_max_active_jobs")]

    operations = [migrations.RunPython(limit_existing_trial, migrations.RunPython.noop)]
