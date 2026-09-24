from django.db import migrations


def assign_bamako_district(apps, schema_editor):
    Region = apps.get_model("locations", "Region")
    City = apps.get_model("locations", "City")
    alias = schema_editor.connection.alias
    district, _ = Region.objects.using(alias).get_or_create(
        name="District de Bamako", defaults={"kind": "DISTRICT", "is_active": True}
    )
    City.objects.using(alias).filter(name__iexact="Bamako").update(region=district)


class Migration(migrations.Migration):
    dependencies = [("locations", "0004_region_city_region")]
    operations = [migrations.RunPython(assign_bamako_district, migrations.RunPython.noop)]
