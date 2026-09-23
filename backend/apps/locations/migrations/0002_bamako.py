from django.db import migrations


def add_bamako(apps, schema_editor):
    City = apps.get_model("locations", "City")
    City.objects.using(schema_editor.connection.alias).get_or_create(name="Bamako")


class Migration(migrations.Migration):
    dependencies = [("locations", "0001_initial")]

    operations = [migrations.RunPython(add_bamako, migrations.RunPython.noop)]
