# Étape 11 — Permissions IDOR et workflow d'intervention

Cette étape termine le bloc 8–11 du roadmap : une demande déjà attribuée devient une intervention privée entre son client et son prestataire.

## Accès privés

Un client continue à lire uniquement ses propres demandes. Un prestataire dispose maintenant de routes séparées pour ses interventions attribuées :

| Méthode | Route | Accès |
| --- | --- | --- |
| GET | `/api/v1/providers/interventions/` | Interventions attribuées au prestataire connecté |
| GET | `/api/v1/providers/interventions/<uuid>/` | Détail de son intervention |
| POST | `/api/v1/providers/interventions/<uuid>/transition/` | Avancer son intervention |
| POST | `/api/v1/requests/<uuid>/confirm/` | Client propriétaire, après fin prestataire |

Un UUID appartenant à un autre client ou à un autre prestataire renvoie `404`. Les QuerySets restent filtrés par propriétaire afin de ne pas révéler l'existence d'un objet privé.

Après attribution, le prestataire peut voir les informations nécessaires à l'intervention, notamment l'adresse précise et le téléphone du client. Le client voit l'identifiant, le nom d'affichage et le téléphone du prestataire qui lui a été attribué.

## Machine d'état

Le chemin normal est strict :

```text
ACCEPTED
  → EN_ROUTE
  → ARRIVED
  → IN_PROGRESS
  → PROVIDER_COMPLETED
  → CLIENT_CONFIRMED
```

Le prestataire contrôle uniquement les quatre transitions jusqu'à `PROVIDER_COMPLETED`. Le client propriétaire contrôle uniquement la confirmation finale. Il est impossible de sauter une étape ou de répéter une transition déjà consommée.

Chaque transition verrouille la demande avec `select_for_update()`, modifie l'état et ajoute une ligne `RequestStatusHistory` dans la même transaction.

## Vérification locale

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py check
& ".\.venv\Scripts\python.exe" backend\manage.py makemigrations --check --dry-run
& ".\.venv\Scripts\python.exe" backend\manage.py test apps.accounts apps.locations apps.catalog apps.providers apps.requests --settings=config.test_settings
git status
```

Aucune migration n'est attendue à cette étape : les statuts nécessaires existent déjà depuis la création du modèle de demande.


## Validation locale du 23 septembre 2026

Validation effectuée avec succès :

- `manage.py check` : aucun problème détecté ;
- `makemigrations --check --dry-run` : aucune migration supplémentaire attendue ;
- suite isolée complète : **38 tests OK** ;
- **1 test PostgreSQL ignoré sous SQLite**, comme prévu ;
- tests IDOR client/prestataire validés ;
- workflow séquentiel jusqu'à `CLIENT_CONFIRMED` validé ;
- correction vérifiée : aucune information de prestataire n'est exposée avant attribution ;
- branche locale propre après validation.
