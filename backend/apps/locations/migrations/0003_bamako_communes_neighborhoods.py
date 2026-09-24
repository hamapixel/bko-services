from django.db import migrations


BAMAKO_COMMUNES = {
    "Commune I": [
        "Banconi",
        "Boulkassoumbougou",
        "Djélibougou",
        "Doumanzana",
        "Fadjiguila",
        "Korofina Nord",
        "Korofina Sud",
        "Sikoroni",
        "Sotuba",
    ],
    "Commune II": [
        "Bagadadji",
        "Bakaribougou",
        "Bozola",
        "Bougouba",
        "Hippodrome",
        "Médina-Coura",
        "Missira",
        "N'Golonina",
        "Niaréla",
        "Quinzambougou",
        "TSF",
        "Zone Industrielle",
    ],
    "Commune III": [
        "Badialan I",
        "Badialan II",
        "Badialan III",
        "Bamako-Coura",
        "Bamako-Coura Bolibana",
        "Centre Commercial",
        "Darsalam",
        "Dravéla",
        "Dravéla Bolibana",
        "Kodabougou",
        "Koulouba",
        "Koulouninko",
        "N'Tomikorobougou",
        "Niomirambougou",
        "Ouolofobougou",
        "Ouolofobougou Bolibana",
        "Point G",
        "Samé",
        "Sirakoro-Dounfing",
        "Sogonafing",
    ],
    "Commune IV": [
        "Djicoroni-Para",
        "Hamdallaye",
        "Kalabambougou",
        "Lafiabougou",
        "Lassa",
        "Sébénikoro",
        "Sibiribougou",
        "Taliko",
    ],
    "Commune V": [
        "Baco-Djicoroni",
        "Badalabougou",
        "Daoudabougou",
        "Kalaban-Coura",
        "Quartier-Mali",
        "Sabalibougou",
        "SEMA I",
        "Torokorobougou",
    ],
    "Commune VI": [
        "Banankabougou",
        "Dianéguéla",
        "Faladié",
        "Magnambougou",
        "Missabougou",
        "Niamakoro",
        "Sénou",
        "Sogoniko",
        "Sokorodji",
        "Yirimadio",
    ],
}


def seed_bamako_areas(apps, schema_editor):
    City = apps.get_model("locations", "City")
    Commune = apps.get_model("locations", "Commune")
    Neighborhood = apps.get_model("locations", "Neighborhood")
    db_alias = schema_editor.connection.alias

    bamako, _ = City.objects.using(db_alias).get_or_create(
        name="Bamako",
        defaults={"is_active": True},
    )
    City.objects.using(db_alias).filter(pk=bamako.pk).update(is_active=True)

    for commune_name, neighborhoods in BAMAKO_COMMUNES.items():
        commune, _ = Commune.objects.using(db_alias).get_or_create(
            city=bamako,
            name=commune_name,
            defaults={"is_active": True},
        )
        Commune.objects.using(db_alias).filter(pk=commune.pk).update(
            is_active=True
        )

        for neighborhood_name in neighborhoods:
            neighborhood, _ = Neighborhood.objects.using(db_alias).get_or_create(
                commune=commune,
                name=neighborhood_name,
                defaults={"is_active": True},
            )
            Neighborhood.objects.using(db_alias).filter(
                pk=neighborhood.pk
            ).update(is_active=True)


class Migration(migrations.Migration):

    dependencies = [
        ("locations", "0002_bamako"),
    ]

    operations = [
        migrations.RunPython(seed_bamako_areas, migrations.RunPython.noop),
    ]
