from django.db import migrations


TRIAL_DESCRIPTION = (
    "Profitez gratuitement de BKO Services pendant 14 jours. "
    "L'essai est activable une seule fois après validation de votre profil."
)


def update_trial_description(apps, schema_editor):
    SubscriptionPlan = apps.get_model("subscriptions", "SubscriptionPlan")
    SubscriptionPlan.objects.filter(code="essai-14j").update(
        description=TRIAL_DESCRIPTION,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("subscriptions", "0006_provider_subscription_pending_plan"),
    ]

    operations = [
        migrations.RunPython(update_trial_description, migrations.RunPython.noop),
    ]
