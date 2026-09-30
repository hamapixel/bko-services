from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("locations", "0006_mali_regions"),
        ("providers", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="providerprofile",
            name="travel_communes",
            field=models.ManyToManyField(
                blank=True,
                help_text="Communes supplémentaires dans lesquelles le prestataire accepte de se déplacer.",
                related_name="travel_providers",
                to="locations.commune",
            ),
        ),
    ]
