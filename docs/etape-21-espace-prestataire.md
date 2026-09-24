# Étape 21 — Espace prestataire responsive

Cette étape livre le deuxième espace métier complet de BKO Services : l'espace prestataire vérifié.

## Parcours livré

Le prestataire peut désormais :

1. se connecter depuis un écran dédié ;
2. accéder uniquement si son compte a le rôle `PROVIDER` et son dossier est `VERIFIED` ;
3. voir son tableau de bord ;
4. consulter ses offres en attente ;
5. voir uniquement le métier, la zone générale et la priorité avant acceptation ;
6. ne jamais voir l'adresse précise ni le téléphone client avant attribution ;
7. accepter une offre via l'API atomique existante ;
8. consulter uniquement ses interventions attribuées ;
9. avancer dans l'ordre `ACCEPTED → EN_ROUTE → ARRIVED → IN_PROGRESS → PROVIDER_COMPLETED` ;
10. voir l'adresse et le téléphone uniquement après attribution ;
11. gérer sa disponibilité pour les nouvelles offres ;
12. consulter son abonnement ;
13. voir les plans disponibles ;
14. préparer une transaction de paiement idempotente ;
15. suivre le statut serveur des paiements ;
16. consulter ses avis clients ;
17. voir ses métiers et quartiers validés.

## Routes frontend

- `/prestataire/connexion` : connexion prestataire ;
- `/prestataire` : tableau de bord ;
- `/prestataire/offres` : offres en attente ;
- `/prestataire/offres/<uuid>` : détail et acceptation ;
- `/prestataire/interventions` : interventions attribuées ;
- `/prestataire/interventions/<uuid>` : détail et workflow ;
- `/prestataire/abonnement` : abonnement, plans et paiements ;
- `/prestataire/avis` : avis reçus ;
- `/prestataire/profil` : profil et disponibilité.

## Authentification

L'espace prestataire utilise la même session Django sécurisée que le reste de l'application :

- cookie de session `HttpOnly` ;
- protection CSRF pour les mutations ;
- aucun token d'authentification dans `localStorage` ;
- appels same-origin via le proxy Next.js `/api/*`.

Le shell prestataire charge :

```text
GET /api/v1/auth/me/
GET /api/v1/providers/application/
```

L'accès est accordé uniquement lorsque :

```text
user.role = PROVIDER
provider.status = VERIFIED
```

La page `/prestataire/connexion` reste volontairement accessible sans passer par le shell protégé.

## Confidentialité des offres

Avant acceptation, une offre expose seulement :

- identifiant de l'offre ;
- identifiant de la demande ;
- métier ;
- quartier ;
- commune ;
- priorité ;
- date de création.

Elle n'expose pas les champs saisis librement par le client ni ses coordonnées privées :

- `title` ;
- `description` ;
- `address_detail` ;
- `client_phone`.

Le titre et la description restent masqués avant attribution car ils peuvent contenir un numéro de téléphone, une adresse ou d'autres informations personnelles. Les tests vérifient explicitement qu'aucune de ces données ne figure dans la réponse d'offre.

## Acceptation atomique

Le frontend appelle :

```text
POST /api/v1/providers/offers/<uuid>/accept/
```

Le frontend ne décide jamais lui-même qu'une mission est attribuée.

Le serveur revérifie au moment exact de l'acceptation :

- que l'offre appartient au prestataire ;
- que le prestataire est vérifié ;
- qu'il est disponible ;
- que son téléphone est vérifié ;
- que son abonnement autorise encore la demande ;
- que l'offre est encore disponible ;
- qu'aucun autre prestataire n'a déjà gagné la demande.

Après succès seulement, le frontend ouvre la page de l'intervention attribuée.

## Interventions attribuées

Le serializer prestataire expose maintenant aussi en lecture seule :

- `trade_name` ;
- `neighborhood_name` ;
- `commune_name`.

L'adresse précise et le téléphone client sont visibles sur ce serializer parce que la requête filtre strictement :

```text
assigned_provider__user = request.user
```

Un autre prestataire continue à recevoir `404` pour un UUID étranger.

## Filtres d'interventions

L'API accepte un filtre de statut validé :

```text
GET /api/v1/providers/interventions/?status=ACCEPTED,EN_ROUTE
```

Les statuts inconnus sont rejetés en `400`.

Le frontend propose :

- Actives ;
- À confirmer par le client ;
- Terminées ;
- Toutes.

La pagination DRF est conservée avec **Charger plus**.

## Workflow prestataire

Le bouton d'action suivant est calculé uniquement à partir du statut serveur :

- `ACCEPTED → EN_ROUTE` : « Je suis en route » ;
- `EN_ROUTE → ARRIVED` : « Je suis arrivé » ;
- `ARRIVED → IN_PROGRESS` : « Commencer l'intervention » ;
- `IN_PROGRESS → PROVIDER_COMPLETED` : « Marquer comme terminée ».

Le frontend appelle :

```text
POST /api/v1/providers/interventions/<uuid>/transition/
```

avec le seul statut suivant attendu.

Le backend reste la source de vérité et refuse toute étape sautée.

Après `PROVIDER_COMPLETED`, le prestataire ne peut pas confirmer la fin à la place du client.

## Disponibilité

Le profil permet d'appeler :

```text
PATCH /api/v1/providers/availability/
```

avec :

```json
{
  "is_available": true
}
```

La disponibilité concerne les nouvelles offres.

Une intervention déjà attribuée reste accessible et doit pouvoir être terminée même si le prestataire devient indisponible ensuite.

Le backend continue à contrôler les prérequis métier avant d'autoriser `is_available = true`.

## Profil prestataire

La représentation privée du propre profil expose maintenant :

- les UUID métiers existants ;
- les UUID zones existantes ;
- `trade_details` avec identifiant et nom ;
- `service_area_details` avec identifiant, quartier et commune.

Ces données servent uniquement à l'affichage du profil du propriétaire.

## Abonnements

L'écran appelle :

```text
GET /api/v1/subscriptions/me/
GET /api/v1/subscriptions/plans/
```

Il affiche :

- plan courant ;
- statut effectif ;
- dates ;
- droit aux demandes normales ;
- droit aux demandes urgentes ;
- plans publics actifs.

Une expiration empêche les nouvelles offres selon les règles backend déjà présentes, mais n'interrompt pas une intervention déjà attribuée.

## Paiements

Le prestataire peut préparer une transaction via :

```text
POST /api/v1/payments/transactions/
```

Le frontend fournit uniquement :

- `plan_id` ;
- une clé d'idempotence générée localement.

Il ne fournit jamais :

- montant ;
- durée ;
- statut de succès ;
- référence fournisseur.

Le serveur dérive le montant et la durée depuis le plan et crée la transaction `PENDING`.

L'interface affiche explicitement :

> Une transaction PENDING n'est pas un paiement réussi.

Seul le webhook serveur signé peut passer la transaction à `SUCCEEDED` et activer ou renouveler l'abonnement.

Aucun bouton frontend ne peut marquer un paiement comme réussi.

## Avis

L'écran avis utilise l'endpoint public existant du profil vérifié :

```text
GET /api/v1/providers/<provider_id>/reviews/
```

Les avis ne contiennent aucune donnée privée du client.

## Responsive

Sur PC :

- sidebar fixe ;
- état de disponibilité visible ;
- topbar ;
- cartes d'offres ;
- grilles intervention/abonnement.

Sur téléphone :

- menu burger ;
- navigation basse ;
- formulaires et cartes en une colonne ;
- bandeau PWA conservé au-dessus de la navigation.

## Tests backend ajoutés

Deux nouveaux tests sont ajoutés :

1. une offre fournit uniquement les métadonnées sûres sans titre, description, adresse ni téléphone ;
2. les filtres d'interventions acceptent uniquement les statuts valides.

Les tests existants sont aussi enrichis pour vérifier :

- les libellés métier/quartier/commune des interventions ;
- les noms métiers et zones dans le profil privé du prestataire.

Le total attendu passe de **105 à 107 tests**.

## Validation locale

Aucune migration Django n'est ajoutée.

Depuis la racine du dépôt :

```powershell
git pull --ff-only origin feature/provider-space
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

Résultat attendu :

- Django check : OK ;
- aucune migration ;
- lint : OK ;
- build Next.js : OK ;
- **107 tests OK** ;
- 1 test PostgreSQL ignoré sous SQLite ;
- working tree propre.

## Test intégré navigateur

Après réussite de la validation technique, lancer deux terminaux.

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

Ouvrir :

```text
http://localhost:3000/prestataire/connexion
```

Pour le test fonctionnel complet, il faut utiliser un compte réellement `PROVIDER`, vérifié et avec téléphone vérifié. Les scénarios seront testés après réussite de `lint`, `build` et des tests backend.


## Validation locale du 24 septembre 2026

Validation effectuée avec succès :

- `npm.cmd run lint` : **OK** avant le correctif final de confidentialité ;
- correctif final limité au contrat d'offre, aux types TypeScript, au rendu d'offre et à la documentation, sans nouveau hook ni import inutilisé ;
- `npm.cmd run build` après le correctif final : **OK** avec Next.js 16.3.6 / Turbopack ;
- TypeScript : **OK** ;
- routes prestataire générées : `/prestataire`, `/prestataire/abonnement`, `/prestataire/avis`, `/prestataire/connexion`, `/prestataire/interventions`, `/prestataire/interventions/[id]`, `/prestataire/offres`, `/prestataire/offres/[id]`, `/prestataire/profil` ;
- `manage.py check` : aucun problème ;
- `makemigrations --check --dry-run` : aucune modification détectée ;
- suite complète backend : **107 tests OK** ;
- **1 test PostgreSQL ignoré sous SQLite**, comme prévu ;
- confidentialité avant attribution validée : aucun `title`, `description`, `address_detail` ni `client_phone` dans les offres ;
- branche locale propre après validation.
