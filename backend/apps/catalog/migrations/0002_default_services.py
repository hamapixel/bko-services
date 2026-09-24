from django.db import migrations


CATALOG = [
    (
        "Électricité & solaire",
        10,
        [
            ("Électricien bâtiment", "Installation, dépannage et mise aux normes électriques."),
            ("Installateur solaire", "Panneaux solaires, batteries, protections et systèmes autonomes."),
            ("Technicien onduleur / convertisseur", "Installation et dépannage d'onduleurs et convertisseurs."),
            ("Technicien groupe électrogène", "Installation, entretien et dépannage de groupes électrogènes."),
        ],
    ),
    (
        "Plomberie & sanitaire",
        20,
        [
            ("Plombier", "Fuites, tuyauterie, robinetterie et dépannage."),
            ("Installateur sanitaire", "WC, lavabos, douches, chauffe-eau et équipements sanitaires."),
            ("Débouchage & canalisation", "Débouchage et entretien des canalisations."),
            ("Pompe & château d'eau", "Installation et dépannage de pompes et systèmes d'eau."),
        ],
    ),
    (
        "Climatisation & froid",
        30,
        [
            ("Technicien climatisation", "Installation, entretien et dépannage de climatiseurs."),
            ("Frigoriste", "Maintenance et dépannage des équipements frigorifiques."),
            ("Réparateur réfrigérateur / congélateur", "Diagnostic et réparation du froid domestique."),
            ("Entretien climatiseur", "Nettoyage, entretien préventif et contrôle de performance."),
        ],
    ),
    (
        "Bâtiment & finition",
        40,
        [
            ("Maçon", "Construction, réparation et petits travaux de maçonnerie."),
            ("Carreleur", "Pose et réparation de carrelage mural et au sol."),
            ("Peintre bâtiment", "Peinture intérieure et extérieure."),
            ("Plâtrier / staffeur", "Plâtre, staff, faux plafonds et finitions décoratives."),
            ("Étanchéité & toiture", "Recherche de fuites, toiture et travaux d'étanchéité."),
        ],
    ),
    (
        "Menuiserie & métallerie",
        50,
        [
            ("Menuisier bois", "Portes, meubles, fenêtres et réparations en bois."),
            ("Menuisier aluminium", "Portes, fenêtres, vitrines et ouvrages aluminium."),
            ("Soudeur / métallier", "Soudure, grilles, portails et structures métalliques."),
            ("Vitrier", "Pose et remplacement de vitres et miroirs."),
            ("Serrurier", "Serrures, clés, portes et dépannage serrurerie."),
        ],
    ),
    (
        "Électroménager & électronique",
        60,
        [
            ("Réparateur électroménager", "Diagnostic et réparation d'appareils électroménagers."),
            ("Réparateur TV", "Diagnostic et réparation de téléviseurs."),
            ("Réparateur ventilateur", "Entretien et réparation de ventilateurs."),
            ("Installateur antenne / TV", "Installation d'antennes, décodeurs et équipements TV."),
        ],
    ),
    (
        "Informatique & téléphonie",
        70,
        [
            ("Technicien informatique", "Ordinateurs, logiciels, maintenance et dépannage."),
            ("Réparateur téléphone", "Diagnostic et réparation de smartphones et téléphones."),
            ("Technicien réseau / Wi-Fi", "Installation et dépannage de réseaux et Wi-Fi."),
            ("Installateur caméra de surveillance", "Installation et configuration de vidéosurveillance."),
        ],
    ),
    (
        "Automobile & moto",
        80,
        [
            ("Mécanicien automobile", "Entretien et réparation mécanique automobile."),
            ("Mécanicien moto", "Entretien et réparation de motos."),
            ("Électricien automobile", "Diagnostic et réparation électrique automobile."),
            ("Vulcanisateur / pneumatique", "Pneus, crevaisons, chambres à air et entretien."),
        ],
    ),
    (
        "Entretien & maison",
        90,
        [
            ("Nettoyage maison / bureau", "Nettoyage ponctuel ou régulier des locaux."),
            ("Jardinier", "Entretien de jardins, plantes et espaces extérieurs."),
            ("Désinsectisation", "Traitement contre insectes et nuisibles."),
            ("Vidange fosse septique", "Vidange et entretien de fosses septiques."),
            ("Déménagement / manutention", "Aide au transport, déplacement et manutention."),
        ],
    ),
]


def seed_catalog(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Trade = apps.get_model("catalog", "Trade")
    db_alias = schema_editor.connection.alias

    for category_name, category_order, trades in CATALOG:
        category, _ = Category.objects.using(db_alias).get_or_create(
            name=category_name,
            defaults={
                "description": "",
                "display_order": category_order,
                "is_active": True,
            },
        )
        Category.objects.using(db_alias).filter(pk=category.pk).update(
            display_order=category_order,
            is_active=True,
        )

        for trade_order, (trade_name, trade_description) in enumerate(
            trades,
            start=1,
        ):
            trade, _ = Trade.objects.using(db_alias).get_or_create(
                category=category,
                name=trade_name,
                defaults={
                    "description": trade_description,
                    "display_order": trade_order,
                    "is_active": True,
                },
            )
            Trade.objects.using(db_alias).filter(pk=trade.pk).update(
                description=trade_description,
                display_order=trade_order,
                is_active=True,
            )


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_catalog, migrations.RunPython.noop),
    ]
