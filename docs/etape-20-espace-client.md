# Étape 20 — Espace client responsive

Cette étape branche le frontend Next.js sur les API Django déjà sécurisées afin de livrer un véritable espace client responsive.

## Parcours livré

Le client peut désormais :

1. créer un compte CLIENT ;
2. se connecter avec sa session Django ;
3. consulter son tableau de bord ;
4. vérifier son numéro par OTP ;
5. créer une demande normale ou urgente ;
6. sauvegarder explicitement une demande comme brouillon local ;
7. reprendre un brouillon après reconnexion ;
8. consulter l'historique paginé de ses demandes ;
9. filtrer ses demandes ;
10. ouvrir le détail d'une demande ;
11. suivre la timeline des statuts ;
12. voir les coordonnées du prestataire seulement après attribution ;
13. confirmer la fin quand le prestataire a marqué l'intervention terminée ;
14. laisser un seul avis de 1 à 5 étoiles après confirmation.

## Routes frontend

- `/` : accueil public ;
- `/connexion` : connexion / inscription client ;
- `/client` : tableau de bord ;
- `/client/demandes` : historique et filtres ;
- `/client/demandes/nouvelle` : nouvelle demande / reprise de brouillon ;
- `/client/demandes/<uuid>` : détail, timeline, confirmation et avis ;
- `/client/brouillons` : brouillons locaux ;
- `/client/profil` : profil et vérification téléphone.

## Authentification et CSRF

Le frontend utilise les sessions Django existantes.

Les cookies restent `HttpOnly`. Le frontend ne stocke aucun jeton d'authentification dans `localStorage`.

Avant une mutation, le frontend récupère un token via :

```text
GET /api/v1/auth/csrf/
```

Puis il envoie le header :

```text
X-CSRFToken
```

avec les cookies de session.

## Proxy API local

Next.js proxy les routes :

```text
/api/*
```

vers Django via `BKO_API_ORIGIN`.

Valeur de développement par défaut :

```text
http://127.0.0.1:8000
```

Le navigateur continue donc à appeler la même origine Next.js, ce qui simplifie les cookies de session et évite de mettre des identifiants d'API côté client.

Fichier exemple :

```text
frontend/.env.example
BKO_API_ORIGIN=http://127.0.0.1:8000
```

Django accepte en développement les origines frontend locales `localhost:3000` et `127.0.0.1:3000`. En production, `DJANGO_CSRF_TRUSTED_ORIGINS` doit être défini explicitement avec le domaine HTTPS retenu.

## Protection du rôle client

Le layout `/client` charge :

```text
GET /api/v1/auth/me/
```

Un visiteur non connecté est renvoyé vers `/connexion`.

Un compte dont le rôle n'est pas `CLIENT` ne peut pas utiliser l'espace client.

Le rôle n'est jamais choisi par le formulaire d'inscription : le backend continue à imposer `CLIENT`.

## Tableau de bord

Le tableau de bord affiche :

- nombre total de demandes ;
- nombre d'interventions en attente de confirmation client ;
- nombre d'interventions confirmées ;
- nombre de brouillons locaux présents sur l'appareil ;
- cinq demandes récentes.

Les compteurs serveur utilisent le champ `count` de la pagination DRF.

## Historique et filtres

L'API client accepte désormais deux filtres validés :

```text
GET /api/v1/requests/?status=ACCEPTED,EN_ROUTE
GET /api/v1/requests/?priority=URGENT
```

Les valeurs inconnues sont rejetées en `400`.

Les filtres frontend disponibles sont :

- Toutes ;
- Actives ;
- Terminées ;
- Urgentes.

La pagination DRF est conservée et le bouton **Charger plus** ajoute les pages suivantes.

## Métadonnées d'affichage

La représentation privée d'une demande client expose désormais en lecture seule :

- `trade_name` ;
- `neighborhood_name` ;
- `commune_name` ;
- `has_review`.

Ces champs évitent des appels frontend inutiles.

Les protections IDOR existantes restent inchangées : un autre client ne peut pas obtenir la demande par UUID.

## Nouvelle demande

Le formulaire utilise exactement les champs backend autorisés :

- métier ;
- quartier ;
- titre ;
- description ;
- adresse précise ;
- priorité normale ou urgente.

Le formulaire guide d'abord le client par :

- catégorie → métier ;
- ville → commune → quartier.

L'adresse précise reste privée jusqu'à l'attribution d'un prestataire.

## Téléphone vérifié obligatoire

Le backend exige déjà un téléphone vérifié pour créer une demande.

Le frontend reproduit cette règle seulement comme aide UX :

- le bouton d'envoi est désactivé si le téléphone n'est pas vérifié ;
- un lien conduit vers le profil pour demander et saisir le code OTP.

Le backend reste la source de vérité et revérifie cette condition.

## Brouillons hors connexion

Le brouillon est stocké en IndexedDB avec :

```text
state = LOCAL_DRAFT
```

La catégorie, la ville et la commune sont conservées comme contexte local afin que les listes déroulantes puissent être restaurées.

Le brouillon :

- n'est pas une demande serveur ;
- ne reçoit jamais un faux UUID serveur ;
- n'est jamais envoyé silencieusement ;
- n'est supprimé qu'après une création serveur réussie.

Si l'utilisateur clique sur **Envoyer la demande** hors connexion, le garde réseau détecte l'absence de connexion avant même la récupération du token CSRF et conserve la saisie comme brouillon non envoyé.

## Détail et timeline

La page détail affiche :

- métier ;
- quartier et commune ;
- adresse ;
- description ;
- priorité ;
- statut courant ;
- historique des transitions ;
- prestataire attribué ;
- numéro du prestataire seulement après attribution.

Les statuts sont affichés à partir des valeurs réelles du backend.

## Confirmation client

Le bouton **Confirmer la fin** n'apparaît que lorsque :

```text
status = PROVIDER_COMPLETED
```

Il appelle :

```text
POST /api/v1/requests/<uuid>/confirm/
```

Le backend reste responsable de vérifier le propriétaire de la demande et la transition autorisée.

## Avis

Après :

```text
CLIENT_CONFIRMED
```

et seulement si `has_review = false`, le client peut publier :

- une note de 1 à 5 ;
- un commentaire facultatif.

L'API conserve la contrainte d'un seul avis par demande.

Après création, `has_review` devient `true` dans le détail de la demande.

## Profil

Le client peut modifier :

- prénom ;
- nom ;
- e-mail.

Le numéro de connexion n'est pas modifiable depuis cet écran.

La vérification téléphone utilise les endpoints OTP existants.

## Responsive

Sur PC :

- sidebar fixe ;
- topbar ;
- cartes larges ;
- grille de détails.

Sur téléphone :

- sidebar burger ;
- navigation basse ;
- formulaires en une colonne ;
- cartes et actions empilées ;
- bandeau PWA déplacé au-dessus de la navigation basse.

## Validation locale

Aucune migration n'est ajoutée à cette étape.

Depuis la racine :

```powershell
git pull --ff-only origin feature/client-space
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

La suite backend attendue passe de **104 à 105 tests**, car l'étape ajoute un test des filtres de l'historique client.

## Test intégré local

Pour tester réellement connexion + sessions + création de demande, lancer Django et Next.js dans deux terminaux.

Terminal 1 :

```powershell
cd "C:\Users\HP USER\bko-services"
& ".\.venv\Scripts\python.exe" backend\manage.py runserver 127.0.0.1:8000
```

Terminal 2 :

```powershell
cd "C:\Users\HP USER\bko-services\frontend"
npm.cmd run dev
```

Puis ouvrir :

```text
http://localhost:3000
```

Le proxy Next.js enverra les requêtes `/api/*` vers Django.

La validation fonctionnelle navigateur sera faite après réussite de `lint`, `build` et des tests backend.


## Validation locale du 24 septembre 2026

Validation effectuée avec succès :

- `npm.cmd run lint` : **OK** ;
- `npm.cmd run build` : **OK** avec Next.js 16.3.6 / Turbopack ;
- TypeScript : **OK** ;
- routes générées : `/`, `/client`, `/client/brouillons`, `/client/demandes`, `/client/demandes/[id]`, `/client/demandes/nouvelle`, `/client/profil`, `/connexion`, `/manifest.webmanifest`, `/offline` ;
- `manage.py check` : aucun problème ;
- `makemigrations --check --dry-run` : aucune modification détectée ;
- suite complète backend : **105 tests OK** ;
- **1 test PostgreSQL ignoré sous SQLite**, comme prévu ;
- branche locale propre après validation.
