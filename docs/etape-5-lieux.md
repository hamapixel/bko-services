# Étape 5 — Villes, communes et quartiers

Cette étape crée trois modèles administrables : une ville contient des communes et chaque commune contient des quartiers. Chaque identifiant est un UUID. Une contrainte en base évite les doublons de nom dans une même ville ou commune, y compris les différences de majuscules. Les enfants ne sont pas supprimés par la suppression accidentelle d'un parent (`PROTECT`). Désactiver un parent masque aussi ses descendants dans l'API publique.

La migration `locations.0002_bamako` crée uniquement la ville **Bamako**. Ajoutez et vérifiez les noms des communes et quartiers dans `/django-admin/` avant de les afficher aux utilisateurs. Seuls les comptes autorisés à gérer ces modèles dans l'administration peuvent les créer ou les modifier ; l'API exposée ici est uniquement en lecture.

| Méthode | Route | Usage |
| --- | --- | --- |
| GET | `/api/v1/locations/cities/` | Villes actives |
| GET | `/api/v1/locations/communes/?city=<uuid>` | Communes actives de la ville |
| GET | `/api/v1/locations/neighborhoods/?commune=<uuid>` | Quartiers actifs de la commune |

Ces listes sont publiques et paginées par 20 éléments (`count`, `next`, `previous`, `results`). Un UUID de filtre mal formé renvoie `400`. Aucune route publique d'écriture n'est ajoutée.

## Vérification sous Windows

Depuis la racine du dépôt, après avoir récupéré `feature/locations` :

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py check
& ".\.venv\Scripts\python.exe" backend\manage.py test apps.accounts apps.locations --settings=config.test_settings
& ".\.venv\Scripts\python.exe" backend\manage.py migrate --plan
```

Le plan doit seulement prévoir `locations.0001_initial` et `locations.0002_bamako`. Si c'est le cas :

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py migrate --noinput
& ".\.venv\Scripts\python.exe" backend\manage.py showmigrations locations
& ".\.venv\Scripts\python.exe" backend\manage.py shell -c "from apps.locations.models import City; print(list(City.objects.values_list('name', flat=True)))"
git status
```

Résultat attendu : les deux migrations `[X]`, puis `['Bamako']` si aucune autre ville n'a été ajoutée. Les tests isolés utilisent SQLite et ne modifient pas votre base PostgreSQL. L'ajout des communes et quartiers se fera depuis l'administration une fois les noms vérifiés.
