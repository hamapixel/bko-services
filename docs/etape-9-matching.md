# Étape 9 — Recherche de prestataires et offres individuelles

Le superadministrateur lance la recherche sur une demande `CREATED` depuis l'action « Créer les offres » de `/django-admin/`. Un administrateur délégué doit disposer en plus de la permission `requests.dispatch_request`. Le moteur vérifie le métier et le quartier actifs de la demande, puis sélectionne uniquement les prestataires **vérifiés, disponibles, au téléphone vérifié, actifs, compétents et présents dans le quartier**. L'ordre initial de sélection est la date de vérification, puis l'UUID. Il produit **une offre au maximum** pour une demande normale et **cinq au maximum** pour une demande urgente.

La recherche, l'historique des statuts et les offres sont écrits dans une transaction. `CREATED → SEARCHING → OFFERED` quand au moins une offre existe. Sans candidat, la demande reste `SEARCHING` et l'administrateur peut relancer la recherche plus tard ; il n'y a pas encore de relance automatique. Une demande déjà `OFFERED` ne peut pas être redistribuée par cette action, et la base interdit deux offres au même prestataire pour la même demande.

| Méthode | Route | Accès |
| --- | --- | --- |
| GET | `/api/v1/providers/offers/` | Ses offres en attente seulement |
| GET | `/api/v1/providers/offers/<uuid>/` | Détail d'une offre qui lui appartient |

Le destinataire voit seulement l'identifiant de l'offre et de la demande, le métier, le quartier, la priorité et la date. L'adresse précise, le numéro, le nom légal du client, le titre et la description **ne sont pas transmis** : les champs libres peuvent contenir des coordonnées. Un UUID d'offre étrangère renvoie `404`. Aucune notification, acceptation ou attribution n'est encore activée ; l'étape suivante ajoutera l'acceptation atomique et revérifiera l'éligibilité du prestataire. Les tests de concurrence sur PostgreSQL seront ajoutés avec cette opération.

## Vérification sous Windows

Depuis la racine du dépôt après avoir récupéré `feature/matching-offers` :

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py check
& ".\.venv\Scripts\python.exe" backend\manage.py test apps.accounts apps.locations apps.catalog apps.providers apps.requests --settings=config.test_settings
& ".\.venv\Scripts\python.exe" backend\manage.py migrate --plan
```

Le plan doit contenir uniquement `requests.0002_alter_servicerequest_options_serviceoffer`. Après vérification :

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py migrate --noinput
& ".\.venv\Scripts\python.exe" backend\manage.py showmigrations requests
& ".\.venv\Scripts\python.exe" backend\manage.py shell -c "from apps.requests.models import ServiceOffer; print('Offres :', ServiceOffer.objects.count())"
git status
```

Résultat attendu si aucune demande réelle n'a été traitée : `[X] 0002_alter_servicerequest_options_serviceoffer`, puis `Offres : 0`. Les tests utilisent SQLite en mémoire et ne modifient pas votre base PostgreSQL locale.
