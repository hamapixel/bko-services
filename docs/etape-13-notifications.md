# Étape 13 — Centre de notifications internes

Cette étape ajoute le centre de notifications stocké dans PostgreSQL. Elle ne déclenche encore ni Web Push, ni SMS, ni notification système du téléphone.

## Objectif

Chaque utilisateur authentifié dispose de ses propres notifications. Une notification contient :

- un type d'événement ;
- un titre ;
- un message court ;
- la demande concernée ;
- sa date de création ;
- sa date de lecture éventuelle.

Aucune notification n'expose les données privées d'un autre compte.

## Événements couverts

Le backend crée une notification interne pour les événements suivants :

| Événement | Destinataire |
| --- | --- |
| Une offre de demande est créée | Prestataire concerné |
| Une offre est acceptée | Client propriétaire |
| Une offre concurrente devient indisponible | Prestataire concerné |
| Prestataire en route | Client |
| Prestataire arrivé | Client |
| Intervention commencée | Client |
| Prestataire marque l'intervention terminée | Client |
| Client confirme la fin | Prestataire attribué |
| Client laisse un avis | Prestataire attribué |

Les notifications internes sont écrites dans la **même transaction** que l'événement métier. Si l'opération métier est annulée par rollback, la notification l'est aussi.

Les effets externes Web Push et SMS restent séparés et seront ajoutés dans les étapes suivantes. Ils devront être déclenchés après commit.

## API privée

| Méthode | Route | Fonction |
| --- | --- | --- |
| GET | `/api/v1/notifications/` | Lister ses notifications |
| GET | `/api/v1/notifications/?unread=true` | Lister uniquement les non-lues |
| GET | `/api/v1/notifications/unread-count/` | Compteur non lu |
| POST | `/api/v1/notifications/<uuid>/read/` | Marquer une notification comme lue |
| POST | `/api/v1/notifications/read-all/` | Tout marquer comme lu |

Les QuerySets sont toujours filtrés par `recipient=request.user`. Un UUID appartenant à un autre utilisateur renvoie `404`.

## Intégrité

La base contient une contrainte d'unicité sur :

`recipient + service_request + kind`

pour éviter de créer deux fois le même événement sur une même demande.

Un index `recipient + read_at + created_at` accélère l'affichage du centre et le compteur des notifications non lues.

## Vérification locale

Depuis la racine du dépôt :

```powershell
git pull --ff-only origin feature/notifications
git status

& ".\.venv\Scripts\python.exe" backend\manage.py check
& ".\.venv\Scripts\python.exe" backend\manage.py makemigrations --check --dry-run
& ".\.venv\Scripts\python.exe" backend\manage.py migrate --plan

& ".\.venv\Scripts\python.exe" backend\manage.py test apps.notifications --settings=config.test_settings
& ".\.venv\Scripts\python.exe" backend\manage.py test apps.accounts apps.locations apps.catalog apps.providers apps.requests apps.reviews apps.notifications --settings=config.test_settings
```

La migration attendue est `notifications.0001_initial`.

Après validation des tests :

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py migrate --noinput
& ".\.venv\Scripts\python.exe" backend\manage.py showmigrations notifications
git status
```
