from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("subscriptions", "0007_update_trial_description"),
    ]

    operations = [
        migrations.AlterField(
            model_name="subscriptionhistory",
            name="action",
            field=models.CharField(
                choices=[
                    ("ACTIVATED", "Activation"),
                    ("RENEWED", "Renouvellement"),
                    ("PLAN_CANCEL", "Changement de plan annulé"),
                    ("CANCELLED", "Annulation"),
                    ("EXPIRED", "Expiration"),
                ],
                max_length=12,
            ),
        ),
    ]
