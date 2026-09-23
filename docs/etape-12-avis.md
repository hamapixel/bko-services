# Étape 12 — Avis clients

Cette étape ouvre le bloc 12–16 du roadmap avec les avis laissés après une intervention réellement terminée.

## Règles métier

Un avis peut être créé uniquement lorsque :

- la demande appartient au client connecté ;
- la demande est à l'état `CLIENT_CONFIRMED` ;
- un prestataire a réellement été attribué ;
- aucun avis n'existe encore pour cette intervention.

La note est comprise entre **1 et 5**. Le commentaire est optionnel et limité à 1000 caractères.

Le client ne choisit jamais manuellement le prestataire à noter : le backend utilise automatiquement `assigned_provider` de la demande. Cela empêche de noter un autre prestataire avec un UUID manipulé.

## Intégrité

Le modèle `Review` contient :

- la demande en `OneToOneField` ;
- le client propriétaire ;
- le prestataire attribué ;
- la note ;
- le commentaire ;
- la date de création.

La relation `OneToOneField` garantit au niveau de la base qu'une intervention ne peut avoir qu'un seul avis. Une contrainte SQL impose également une note entre 1 et 5.

La création verrouille la demande avec `select_for_update()` afin que deux requêtes concurrentes ne puissent pas créer deux avis.

## API

| Méthode | Route | Accès |
| --- | --- | --- |
| POST | `/api/v1/requests/<uuid>/review/` | Client propriétaire |
| GET | `/api/v1/providers/<uuid>/reviews/` | Public |

Exemple de création :

```json
{
  "rating": 5,
  "comment": "Très bon service."
}
```

La liste publique n'expose ni l'identité ni le téléphone du client.

## Vérification locale

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py check
& ".\.venv\Scripts\python.exe" backend\manage.py migrate --plan
& ".\.venv\Scripts\python.exe" backend\manage.py test apps.accounts apps.locations apps.catalog apps.providers apps.requests apps.reviews --settings=config.test_settings
git status
```

La migration attendue est `reviews.0001_initial`.


## Validation locale du 23 septembre 2026

Validation effectuée avec succès :

- `manage.py check` : aucun problème détecté ;
- `makemigrations --check --dry-run` : aucun changement non versionné ;
- `migrate --plan` : `reviews.0001_initial` détectée comme prévu ;
- tests de l'application avis : **8 tests OK** ;
- suite complète : **46 tests OK** ;
- **1 test PostgreSQL ignoré sous SQLite**, comme prévu ;
- migration `reviews.0001_initial` appliquée localement ;
- `showmigrations reviews` affiche `[X] 0001_initial` ;
- branche locale propre après validation.
