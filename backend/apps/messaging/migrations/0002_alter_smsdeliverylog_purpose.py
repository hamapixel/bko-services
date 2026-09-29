from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("messaging", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="smsdeliverylog",
            name="purpose",
            field=models.CharField(
                choices=[
                    ("PHONE_VERIFICATION", "Vérification du téléphone"),
                    ("PASSWORD_RESET", "Réinitialisation du mot de passe"),
                ],
                max_length=32,
            ),
        ),
    ]
