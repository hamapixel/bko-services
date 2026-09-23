# Étape 16 — Plaintes et signalements

Cette étape ajoute un traitement privé des plaintes liées à une intervention attribuée.

## Règles métier

Une plainte peut être ouverte uniquement par :

- le client propriétaire de la demande ;
- le prestataire effectivement attribué à cette intervention.

Un utilisateur extérieur reçoit un `404` afin de ne pas révéler l'existence d'une intervention étrangère.

Une plainte n'est autorisée que si un prestataire est déjà attribué et si l'intervention est dans l'un des états suivants :

- `ACCEPTED` ;
- `EN_ROUTE` ;
- `ARRIVED` ;
- `IN_PROGRESS` ;
- `PROVIDER_COMPLETED` ;
- `CLIENT_CONFIRMED`.

Les états `CREATED`, `SEARCHING`, `OFFERED` et `CANCELLED` ne peuvent pas être contestés via ce parcours.

## Passage en DISPUTED

Lorsqu'une plainte valide est créée :

1. l'état courant de l'intervention est mémorisé dans la plainte ;
2. la plainte passe à `OPEN` ;
3. une entrée `ComplaintStatusHistory` est créée ;
4. l'intervention passe à `DISPUTED` ;
5. une entrée `RequestStatusHistory` trace le passage vers `DISPUTED`.

Pendant `DISPUTED`, le workflow normal de l'intervention ne peut plus avancer.

Une seule plainte active est autorisée par intervention. La base de données impose cette règle pour les états `OPEN` et `UNDER_REVIEW`.

## Catégories

Les catégories disponibles sont :

- `SERVICE_QUALITY` : qualité du service ;
- `BEHAVIOR` : comportement ;
- `PAYMENT` : paiement ;
- `SAFETY` : sécurité ;
- `OTHER` : autre.

La description est limitée à 2 000 caractères.

## Traitement administratif

Seuls les utilisateurs actifs de rôle `ADMIN` ou `SUPERADMIN` peuvent consulter la file administrative et changer l'état d'une plainte.

Transitions autorisées :

```text
OPEN -> UNDER_REVIEW
OPEN -> RESOLVED
OPEN -> REJECTED

UNDER_REVIEW -> RESOLVED
UNDER_REVIEW -> REJECTED
```

Une plainte clôturée ne peut plus être modifiée.

Pour `RESOLVED` ou `REJECTED`, une note de décision est obligatoire.

Lors de la décision finale :

1. la plainte reçoit la note et `resolved_at` ;
2. l'intervention doit encore être en `DISPUTED` ;
3. son état précédent est restauré exactement ;
4. cette restauration est ajoutée à `RequestStatusHistory`.

Ainsi, une intervention mise en pause à `IN_PROGRESS` revient à `IN_PROGRESS` après clôture du litige.

## Confidentialité et IDOR

Un client ou un prestataire ne voit que les plaintes qu'il a lui-même ouvertes.

Routes utilisateur :

| Méthode | Route | Usage |
| --- | --- | --- |
| GET | `/api/v1/complaints/` | Liste de ses propres plaintes |
| POST | `/api/v1/complaints/` | Ouvre une plainte |
| GET | `/api/v1/complaints/<uuid>/` | Détail de sa propre plainte |

Routes ADMIN/SUPERADMIN :

| Méthode | Route | Usage |
| --- | --- | --- |
| GET | `/api/v1/complaints/admin/` | Toutes les plaintes |
| GET | `/api/v1/complaints/admin/<uuid>/` | Détail administratif |
| POST | `/api/v1/complaints/admin/<uuid>/transition/` | Transition de statut |

Un UUID étranger renvoie `404` côté utilisateur. Les routes d'administration renvoient `403` aux rôles non autorisés.

## Audit

Deux historiques sont conservés :

- `ComplaintStatusHistory` pour chaque étape de traitement de la plainte ;
- `RequestStatusHistory` pour le passage à `DISPUTED` et la restauration finale.

L'administration Django expose ces objets en lecture seule afin d'éviter les modifications directes qui contourneraient les services métier.

## Limitation d'abus

La création de plaintes utilise le scope DRF :

```text
complaint_create = 5/day
```

La contrainte de base de données « une plainte active par intervention » reste la protection principale contre deux dossiers concurrents sur la même intervention.

## Validation locale

Depuis la racine du dépôt :

```powershell
git pull --ff-only origin feature/complaints
git status

& ".\.venv\Scripts\python.exe" backend\manage.py check
& ".\.venv\Scripts\python.exe" backend\manage.py makemigrations --check --dry-run
& ".\.venv\Scripts\python.exe" backend\manage.py migrate --plan

& ".\.venv\Scripts\python.exe" backend\manage.py test apps.complaints --settings=config.test_settings

& ".\.venv\Scripts\python.exe" backend\manage.py test apps.accounts apps.locations apps.catalog apps.providers apps.requests apps.reviews apps.notifications apps.messaging apps.complaints --settings=config.test_settings
```

La migration attendue est :

```text
complaints.0001_initial
    Create model Complaint
    Create model ComplaintStatusHistory
```

Après validation :

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py migrate --noinput
& ".\.venv\Scripts\python.exe" backend\manage.py showmigrations complaints
git status
```


## Validation locale du 23 septembre 2026

Validation effectuée avec succès :

- tests de l'application `complaints` : **9 tests OK** ;
- suite complète backend : **78 tests OK** ;
- **1 test PostgreSQL ignoré sous SQLite**, comme prévu ;
- migration `complaints.0001_initial` appliquée localement ;
- `showmigrations complaints` affiche `[X] 0001_initial` ;
- branche locale propre après validation.
