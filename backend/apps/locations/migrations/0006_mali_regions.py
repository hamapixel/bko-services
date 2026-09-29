from django.db import migrations


# Régions de la carte administrative de 2023. Les villes, communes et quartiers
# sont ajoutés après vérification locale ; une région seule n'ouvre pas le service.
REGIONS = (
    "Kayes", "Koulikoro", "Sikasso", "Ségou", "Mopti", "Tombouctou",
    "Gao", "Kidal", "Taoudénit", "Ménaka", "Nioro", "Kita",
    "Dioïla", "Nara", "Bougouni", "Koutiala", "San", "Douentza",
    "Bandiagara",
)


def seed_regions(apps, schema_editor):
    Region = apps.get_model("locations", "Region")
    manager = Region.objects.using(schema_editor.connection.alias)
    for name in REGIONS:
        if not manager.filter(name__iexact=name).exists():
            manager.create(name=name, kind="REGION", is_active=True)


class Migration(migrations.Migration):
    dependencies = [("locations", "0005_bamako_district")]
    operations = [migrations.RunPython(seed_regions, migrations.RunPython.noop)]
