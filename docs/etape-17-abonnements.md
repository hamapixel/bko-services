# Étape 17 — Plans et abonnements prestataires

Cette étape ajoute les plans d'abonnement et les droits associés aux prestataires. Le paiement réel reste hors périmètre et sera traité à l'étape 18.

## Principes

Un prestataire doit désormais disposer d'un abonnement effectivement actif pour recevoir une nouvelle offre.

L'abonnement ne coupe pas une intervention déjà attribuée. Les droits sont contrôlés :

1. lors du matching avant de créer une offre ;
2. une seconde fois au moment où le prestataire tente d'accepter l'offre.

Ainsi, si l'abonnement expire entre ces deux moments, l'offre ne peut plus être acceptée.

## Plans

Le modèle `SubscriptionPlan` est administrable et contient :

- code unique ;
- nom ;
- description ;
- prix en FCFA (`price_xof`) ;
- durée en jours ;
- droit de recevoir des demandes ;
- droit supplémentaire de recevoir des demandes urgentes ;
- activation/désactivation commerciale ;
- ordre d'affichage.

Une durée inférieure à un jour est interdite.

Un plan ne peut pas autoriser les urgences s'il n'autorise pas les demandes normales.

Désactiver un plan empêche les nouvelles activations/renouvellements sur ce plan. Cela ne retire pas automatiquement les droits d'un abonnement déjà en cours.

## Abonnement prestataire

Un seul abonnement courant existe par prestataire.

Statuts stockés :

- `ACTIVE` ;
- `CANCELLED` ;
- `EXPIRED`.

La période est définie par `starts_at` et `ends_at`.

L'état effectif tient toujours compte de la date. Un abonnement stocké `ACTIVE` dont `ends_at` est dépassé est traité immédiatement comme expiré pour le matching, l'acceptation et l'API prestataire.

Aucune tâche asynchrone n'est nécessaire pour empêcher l'utilisation d'un abonnement expiré.

## Droits

Les droits V1 sont volontairement simples :

- `can_receive_requests` : recevoir les nouvelles demandes normales ;
- `can_receive_urgent_requests` : recevoir aussi les demandes urgentes.

Le matching filtre les prestataires par abonnement en plus des règles déjà existantes : compte actif, téléphone vérifié, profil vérifié, disponibilité, métier et zone.

## Cycle de vie administratif

L'activation, le renouvellement et l'annulation sont réservés :

- au `SUPERADMIN` ;
- ou à un utilisateur `ADMIN` actif, staff, possédant la permission Django `subscriptions.manage_subscriptions`.

### Activation

L'activation :

- exige un prestataire vérifié avec téléphone vérifié ;
- exige un plan actif ;
- commence immédiatement ;
- calcule `ends_at` selon `duration_days` ;
- refuse un deuxième abonnement encore actif.

Un abonnement expiré ou annulé peut être réactivé via le même enregistrement courant.

### Renouvellement

Si l'abonnement est encore actif, la nouvelle durée est ajoutée à la date de fin existante.

S'il est expiré, le nouveau cycle repart de la date du renouvellement.

Le renouvellement peut également changer de plan.

Un abonnement annulé doit passer par l'action d'activation, pas par le renouvellement.

### Annulation

Une annulation :

- met le statut à `CANCELLED` ;
- conserve `cancelled_at` ;
- retire immédiatement les droits de matching et d'acceptation ;
- exige une note administrative.

## Historique

`SubscriptionHistory` conserve les événements :

- `ACTIVATED` ;
- `RENEWED` ;
- `CANCELLED` ;
- `EXPIRED`.

Chaque ligne conserve un snapshot du code et du nom du plan, la période correspondante, l'acteur et une note éventuelle.

L'historique reste disponible même si le plan est renommé plus tard.

## API

### Prestataire / public

| Méthode | Route | Usage |
| --- | --- | --- |
| GET | `/api/v1/subscriptions/plans/` | Plans actifs visibles |
| GET | `/api/v1/subscriptions/me/` | Abonnement du prestataire connecté |

Un client ne peut pas consulter `/me/` comme s'il était prestataire.

### Administration

| Méthode | Route | Usage |
| --- | --- | --- |
| GET / POST | `/api/v1/subscriptions/admin/plans/` | Lister / créer les plans |
| PATCH | `/api/v1/subscriptions/admin/plans/<uuid>/` | Modifier un plan |
| GET | `/api/v1/subscriptions/admin/subscriptions/` | Liste des abonnements |
| GET | `/api/v1/subscriptions/admin/providers/<provider_uuid>/` | Abonnement d'un prestataire |
| POST | `/api/v1/subscriptions/admin/providers/<provider_uuid>/activate/` | Activer / réactiver |
| POST | `/api/v1/subscriptions/admin/subscriptions/<uuid>/renew/` | Renouveler |
| POST | `/api/v1/subscriptions/admin/subscriptions/<uuid>/cancel/` | Annuler |

Les champs inattendus sont rejetés sur les mutations.

## Paiement

Aucun paiement n'est simulé à cette étape.

Les abonnements sont activés administrativement afin de valider les règles métier. L'étape 18 ajoutera le paiement et devra appeler ces services seulement après confirmation fiable du paiement côté serveur.

Le frontend ne devra jamais pouvoir déclarer lui-même un abonnement payé ou actif.

## Django Admin

Les plans peuvent être gérés dans le Django Admin.

Les abonnements et leur historique y sont en lecture seule pour éviter de contourner les services métier d'activation, renouvellement et annulation.

## Validation locale

Depuis la racine du dépôt :

```powershell
git pull --ff-only origin feature/subscriptions
git status

& ".\.venv\Scripts\python.exe" backend\manage.py check
& ".\.venv\Scripts\python.exe" backend\manage.py makemigrations --check --dry-run
& ".\.venv\Scripts\python.exe" backend\manage.py migrate --plan

& ".\.venv\Scripts\python.exe" backend\manage.py test apps.subscriptions --settings=config.test_settings

& ".\.venv\Scripts\python.exe" backend\manage.py test apps.accounts apps.locations apps.catalog apps.providers apps.requests apps.reviews apps.notifications apps.messaging apps.complaints apps.subscriptions --settings=config.test_settings
```

La migration attendue est :

```text
subscriptions.0001_initial
    Create model SubscriptionPlan
    Create model ProviderSubscription
    Create model SubscriptionHistory
```

Après validation :

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py migrate --noinput
& ".\.venv\Scripts\python.exe" backend\manage.py showmigrations subscriptions
git status
```

Les tests de l'étape 17 n'effectuent aucun paiement et n'appellent aucun fournisseur externe.


## Validation locale du 24 septembre 2026

Validation effectuée avec succès :

- tests de l'application `subscriptions` : **12 tests OK** ;
- suite complète backend : **90 tests OK** ;
- **1 test PostgreSQL ignoré sous SQLite**, comme prévu ;
- migration `subscriptions.0001_initial` déjà appliquée localement ;
- `showmigrations subscriptions` affiche `[X] 0001_initial` ;
- branche locale propre après validation.
