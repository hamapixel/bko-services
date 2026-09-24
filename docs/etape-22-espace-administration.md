# Étape 22 — Espace administration responsive

Cette étape livre l'espace métier administration de BKO Services dans la même application Next.js, séparé du Django Admin technique disponible sous `/django-admin/`.

## Objectifs

L'administration responsive permet de superviser la plateforme sans contourner les permissions Django.

Elle couvre :

- tableau de bord par compteurs ;
- candidatures prestataires ;
- demandes et matching ;
- plaintes / litiges ;
- abonnements ;
- paiements ;
- utilisateurs en lecture seule.

Aucun rôle utilisateur, mot de passe ou statut financier n'est modifiable directement depuis le frontend.

## Routes frontend

- `/admin/connexion` : connexion administrateur ;
- `/admin` : tableau de bord ;
- `/admin/prestataires` : dossiers prestataires ;
- `/admin/prestataires/<uuid>` : contrôle et décision ;
- `/admin/demandes` : supervision des demandes ;
- `/admin/demandes/<uuid>` : détail privé et matching ;
- `/admin/plaintes` : plaintes ;
- `/admin/plaintes/<uuid>` : traitement d'une plainte ;
- `/admin/abonnements` : plans et abonnements ;
- `/admin/paiements` : audit paiements ;
- `/admin/paiements/<uuid>` : détail et retry fulfillment ;
- `/admin/utilisateurs` : comptes en lecture seule ;
- `/admin/utilisateurs/<uuid>` : détail compte en lecture seule.

## Porte d'entrée API

Les nouvelles routes centrales utilisent :

```text
/api/v1/admin/
```

Elles sont distinctes de :

```text
/django-admin/
```

Le Django Admin reste l'outil technique de secours et de configuration avancée.

## Authentification

L'espace admin utilise :

- la session Django existante ;
- cookie HttpOnly ;
- CSRF pour les mutations ;
- aucun token dans localStorage.

Le shell charge :

```text
GET /api/v1/auth/me/
GET /api/v1/admin/overview/
```

L'overview exige :

- utilisateur authentifié ;
- compte actif ;
- `is_staff = true` ;
- rôle `ADMIN` ou `SUPERADMIN`, ou superuser.

## Capacités dynamiques

L'overview renvoie les capacités du compte :

- `users` ;
- `providers` ;
- `requests` ;
- `dispatch_requests` ;
- `complaints` ;
- `payments` ;
- `subscriptions`.

Le menu frontend masque les sections non autorisées.

### Permissions utilisées

- utilisateurs : `accounts.view_user` ;
- prestataires : `providers.verify_provider` ;
- demandes : `requests.view_servicerequest` ;
- matching : `requests.dispatch_request` ;
- paiements : `payments.manage_payments` ;
- abonnements : `subscriptions.manage_subscriptions` ;
- plaintes : rôle administratif déjà contrôlé par l'application complaints.

Le superuser conserve ses permissions Django natives.

## Tableau de bord

L'overview expose uniquement des compteurs :

- utilisateurs ;
- prestataires en attente ;
- prestataires vérifiés ;
- demandes actives ;
- plaintes ouvertes ou en examen ;
- paiements en attente ;
- paiements réussis mais non appliqués ;
- abonnements effectivement actifs.

Aucune donnée personnelle n'est renvoyée par l'overview.

## Utilisateurs

Endpoints :

```text
GET /api/v1/admin/users/
GET /api/v1/admin/users/<uuid>/
```

Filtres :

- rôle ;
- actif / inactif ;
- recherche sur téléphone, prénom, nom ou e-mail.

La représentation contient uniquement les informations de compte nécessaires à la supervision.

Elle ne contient jamais :

- hash du mot de passe ;
- permissions détaillées ;
- secret OTP.

L'interface est volontairement en lecture seule.

## Prestataires

Endpoints :

```text
GET /api/v1/admin/providers/
GET /api/v1/admin/providers/<uuid>/
POST /api/v1/admin/providers/<uuid>/review/
```

L'accès exige `providers.verify_provider`.

Le dossier expose :

- compte associé ;
- téléphone et état de vérification ;
- nom légal et public ;
- description ;
- métiers ;
- zones ;
- statut ;
- contrôle d'identité booléen ;
- historique des décisions.

Aucune pièce d'identité binaire n'est exposée par cette API.

### Décisions

Le frontend peut demander :

- `APPROVED` ;
- `REJECTED` ;
- `SUSPENDED` ;
- `REOPENED`.

La décision appelle toujours le service existant :

```text
review_provider(...)
```

Le frontend n'attribue jamais lui-même le rôle PROVIDER.

La note de contrôle et la confirmation du contrôle d'identité sont enregistrées dans la même transaction que la décision. Si la décision échoue, la transaction est annulée.

Les exceptions Django métier sont traduites en réponses API 400/403 au lieu d'un HTTP 500.

## Demandes

Endpoints :

```text
GET /api/v1/admin/requests/
GET /api/v1/admin/requests/<uuid>/
POST /api/v1/admin/requests/<uuid>/dispatch/
```

### Liste

La liste ne contient pas :

- téléphone client ;
- adresse précise ;
- titre ;
- description.

Elle contient seulement les métadonnées nécessaires à la supervision.

### Détail

Le détail autorisé contient :

- téléphone client ;
- titre ;
- description ;
- adresse ;
- historique des statuts ;
- offres générées ;
- prestataire attribué.

Ces informations privées sont donc isolées dans une fiche nécessitant `requests.view_servicerequest`.

### Matching

Le bouton matching n'apparaît que si le compte possède :

```text
requests.dispatch_request
```

Le frontend appelle le service existant :

```text
dispatch_request(...)
```

Il ne crée jamais lui-même une offre.

## Plaintes

Les endpoints existants sont réutilisés :

```text
GET /api/v1/complaints/admin/
GET /api/v1/complaints/admin/<uuid>/
POST /api/v1/complaints/admin/<uuid>/transition/
```

Le listing accepte désormais un filtre de statuts validé.

Transitions affichées :

- `OPEN → UNDER_REVIEW` ;
- `OPEN → RESOLVED` ;
- `OPEN → REJECTED` ;
- `UNDER_REVIEW → RESOLVED` ;
- `UNDER_REVIEW → REJECTED`.

Une résolution ou un rejet exige une note.

Le service backend reste responsable de restaurer le statut de l'intervention après la décision finale.

## Paiements

Les endpoints admin existants sont réutilisés :

```text
GET /api/v1/payments/admin/transactions/
GET /api/v1/payments/admin/transactions/<uuid>/
POST /api/v1/payments/admin/transactions/<uuid>/retry-fulfillment/
```

Le listing accepte désormais un filtre de statut validé.

L'interface ne propose aucun bouton permettant de passer une transaction à `SUCCEEDED`.

Seul le webhook signé conserve ce pouvoir.

Le retry fulfillment est affiché uniquement lorsque :

```text
status = SUCCEEDED
fulfilled_at = null
```

Il retente uniquement l'application de l'abonnement.

## Abonnements

Les API existantes sont utilisées :

```text
GET /api/v1/subscriptions/admin/plans/
GET /api/v1/subscriptions/admin/subscriptions/
POST /api/v1/subscriptions/admin/providers/<uuid>/activate/
POST /api/v1/subscriptions/admin/subscriptions/<uuid>/renew/
POST /api/v1/subscriptions/admin/subscriptions/<uuid>/cancel/
```

Un endpoint supplémentaire fournit uniquement les prestataires vérifiés nécessaires au sélecteur d'activation :

```text
GET /api/v1/subscriptions/admin/providers/
```

Il exige `subscriptions.manage_subscriptions` et ne fournit pas le téléphone du prestataire.

L'interface permet :

- activation manuelle ;
- renouvellement avec le même plan ;
- annulation avec motif obligatoire ;
- consultation des plans configurés.

Les règles de durée, droits et audit restent dans les services backend.

## Responsive

Sur PC :

- sidebar administration ;
- topbar ;
- dashboard en grille ;
- listes larges ;
- détails en deux colonnes.

Sur mobile :

- sidebar burger ;
- navigation basse filtrée par permissions ;
- cartes empilées ;
- formulaires et actions en une colonne.

## Tests ajoutés

Cinq nouveaux tests sont ajoutés :

1. porte admin + permission de supervision utilisateurs ;
2. validation prestataire via l'API responsive ;
3. supervision demande + lancement du matching ;
4. filtre admin des plaintes ;
5. filtre admin des paiements.

Le test abonnements existant est enrichi pour couvrir le nouveau sélecteur de prestataires sans ajouter un test séparé.

Le total attendu passe de **107 à 112 tests**.

## Validation locale

Aucune migration n'est ajoutée.

Depuis la racine :

```powershell
git pull --ff-only origin feature/admin-space
git status

& ".\.venv\Scripts\python.exe" backend\manage.py check
& ".\.venv\Scripts\python.exe" backend\manage.py makemigrations --check --dry-run

cd frontend
npm.cmd ci
npm.cmd run lint
npm.cmd run build
cd ..

& ".\.venv\Scripts\python.exe" backend\manage.py test apps.accounts apps.locations apps.catalog apps.providers apps.requests apps.reviews apps.notifications apps.messaging apps.complaints apps.subscriptions apps.payments --settings=config.test_settings

git status
```

Résultats attendus :

- Django check : OK ;
- aucune migration ;
- lint : 0 erreur, 0 warning ;
- build Next.js : OK ;
- **112 tests OK** ;
- 1 test PostgreSQL ignoré sous SQLite ;
- working tree propre.

## Test navigateur

Après validation technique :

Terminal Django :

```powershell
cd "C:\Users\HP USER\bko-services"
& ".\.venv\Scripts\python.exe" backend\manage.py runserver 127.0.0.1:8000
```

Terminal Next.js :

```powershell
cd "C:\Users\HP USER\bko-services\frontend"
npm.cmd run dev
```

Puis ouvrir :

```text
http://localhost:3000/admin/connexion
```

Un compte admin sans permission ne doit voir que les sections correspondant à ses capacités.


## Validation locale du 24 septembre 2026

Validation effectuée avec succès :

- `npm.cmd ci` : **OK** ;
- audit npm : **0 vulnérabilité** ;
- avertissement de support ESLint affiché par npm, non bloquant pour cette étape ;
- avertissement `allow-scripts` pour `unrs-resolver`, non bloquant ; aucun script n'a été approuvé automatiquement ;
- `npm.cmd run lint` : **OK, 0 erreur, 0 warning** ;
- `npm.cmd run build` : **OK** avec Next.js 16.3.6 / Turbopack ;
- TypeScript : **OK** ;
- 26 routes générées, dont tout l'espace `/admin` ;
- `manage.py check` : aucun problème ;
- `makemigrations --check --dry-run` : aucune modification détectée ;
- suite complète backend : **112 tests OK** ;
- **1 test PostgreSQL ignoré sous SQLite**, comme prévu.
