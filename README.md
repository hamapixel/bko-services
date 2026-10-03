# BKO Services

**Le bon professionnel, au bon moment.** BKO Services met en relation des clients et des professionnels dans les zones ouvertes au Mali. Le premier parcours à livrer couvre l'inscription, le choix d'un métier et d'un quartier, la création d'une demande, l'attribution à un professionnel, le suivi de l'intervention et l'avis du client.

> Statut au 2 octobre 2026 : **étapes 0 à 22 développées ; qualité et automatisation validées techniquement ; préparation de production en cours**. La suite backend actuelle a réussi avec **150 tests sur PostgreSQL**, sans test ignoré. Le frontend est contrôlé par ESLint, TypeScript et le build Next.js dans la CI. La préparation production inclut maintenant des images Docker Django/Next.js, une stack Compose isolée et un smoke test Docker automatisé.

Pour ouvrir les abonnements payants avec Wave et Orange Money au Mali, voir [l'obtention des accès marchands et l'intégration](docs/paiements-marchands.md). L'accès Wave est codé mais attend un compte marchand réel ; Orange Money Web Payment nécessite encore l'accord marchand et son adaptateur dédié.

## Principes

- Les clients n'accèdent qu'à leurs demandes ; les professionnels n'accèdent qu'aux offres qui leur sont adressées et aux interventions qui leur sont attribuées. Ces règles sont appliquées dans l'API et couvertes par des tests d'accès par identifiant (IDOR).
- Une demande urgente peut être proposée à cinq professionnels compatibles au maximum. Une transaction PostgreSQL garantit qu'un seul l'accepte.
- Les pièces d'identité et les coordonnées privées doivent rester protégées. Avant attribution, l'offre transmise au professionnel contient seulement les renseignements nécessaires pour décider.
- L'interface mobile reste utilisable avec une connexion instable. Une demande conservée hors connexion est clairement marquée **non envoyée** jusqu'à confirmation du serveur.
- Les prestataires doivent être vérifiés pour recevoir des demandes. Les tarifs, catégories, métiers, quartiers et zones administrables sont gérés côté serveur.

## Architecture retenue

| Composant | Choix | Responsabilité |
| --- | --- | --- |
| API | Django + Django REST Framework | Authentification, droits d'accès, règles métier, administration et API `/api/v1/` |
| Données | PostgreSQL | Données relationnelles, contraintes et attribution atomique |
| Application web | Une application Next.js + TypeScript | Pages publiques et espaces client, prestataire et administrateur ; PWA responsive |
| Tâches (cible) | Celery + Redis, à mettre en place | Notifications, SMS, rappels et expirations hors des requêtes HTTP |
| Notifications | Centre interne + Web Push ; SMS via adaptateur | Alertes et vérification du téléphone, avec suivi des envois |
| Fichiers | Stockage privé pour documents sensibles | Validation des images, accès contrôlé et sauvegardes |

L'architecture, les rôles, l'arborescence prévue et la feuille de route sont détaillés dans [docs/architecture.md](docs/architecture.md).

## État du projet

- [x] Étape 0 : cadrage, architecture, arborescence, README et `.gitignore`.
- [x] Étape 1 : environnement de développement Windows et vérification des outils.
- [x] Étape 2 : création du backend Django/DRF et du frontend Next.js.
- [x] Étape 3 : utilisateur personnalisé, rôles et premières migrations.
- [x] Étape 4 : inscription client, sessions, profil et code de vérification du téléphone en développement local.
- [x] Étape 5 : ville, communes et quartiers administrables ; Bamako initialisé.
- [x] Étape 6 : métiers et catégories de services administrables.
- [x] Étape 7 : candidatures, vérification manuelle et profils de prestataires.
- [x] Étape 8 : création privée des demandes et premier état historisé.
- [x] Étape 9 : recherche des prestataires compatibles et création des offres privées.
- [x] Étape 10 : acceptation atomique d'une offre et attribution unique.
- [x] Étape 11 : permissions IDOR et workflow d'intervention.
- [x] Étape 12 : avis clients après intervention confirmée.
- [x] Étape 13 : centre de notifications internes.
- [x] Étape 14 : Web Push et service worker minimal.
- [x] Étape 15 : SMS/OTP professionnel.
- [x] Étape 16 : plaintes / signalements.
- [x] Étape 17 : plans et abonnements prestataires.
- [x] Étape 18 : paiements sécurisés.
- [x] Étape 19 : PWA complète et hors connexion.
- [x] Étape 20 : espace client responsive.
- [x] Étape 21 : espace prestataire responsive.
- [x] Étape 22 : espace administration responsive.

## Localisation et envoi des demandes

Le choix suit **région ou district → ville → commune → quartier**. Le District de Bamako possède déjà des villes, communes et quartiers. Les 19 régions sont visibles après migration. Dans une région sans localités répertoriées, le client peut saisir ville, commune et quartier ; sa demande reste **Zone à vérifier** jusqu'à ce que l'administration rattache un quartier validé, puis le matching démarre. Les prestataires ne peuvent candidater qu'après ouverture de quartiers actifs. Une migration rattache la ville de Bamako déjà présente à son district. Voir [la couverture et la recherche](docs/couverture-mali-et-recherche.md).

Lorsqu'un client vérifié envoie une demande, le serveur lance immédiatement la recherche et crée des offres privées (jusqu'à trois pour une demande normale ou cinq pour une urgence). La correspondance exige le **même métier** puis applique l'ordre **quartier demandé → autres quartiers de la même commune → autres communes explicitement autorisées par le prestataire**. Le troisième niveau n'est utilisé que s'il reste des places d'offre ; une demande n'est donc jamais envoyée arbitrairement à tous les prestataires de Bamako. Le prestataire gère ses communes de déplacement dans son profil. Il doit aussi être approuvé, disponible, actif, avoir son téléphone vérifié et un abonnement autorisant ce type de demande. Le premier qui accepte est le seul attributaire ; toutes les autres offres en attente sont annulées.

Sans candidat, la demande reste « Recherche en cours » ; les administrateurs sont avertis et voient le compteur des demandes sans offre. La recherche reprend automatiquement lorsqu'un prestataire compatible devient disponible, obtient ou renouvelle un abonnement, termine une intervention qui libère une place ou ajoute une commune de déplacement compatible. La relance manuelle reste possible depuis `/admin/demandes` pour les demandes historiques et les cas particuliers.

## Démarrage sur Windows

Après avoir cloné le dépôt, consulter [l'installation du backend et du frontend](docs/etape-2.md), [le modèle utilisateur](docs/etape-3.md), [l'authentification](docs/etape-4-auth.md), [les lieux](docs/etape-5-lieux.md), [le catalogue](docs/etape-6-catalogue.md), [les prestataires](docs/etape-7-prestataires.md), [les demandes](docs/etape-8-demandes.md), [le matching](docs/etape-9-matching.md) et [l'acceptation atomique](docs/etape-10-acceptation.md), puis [le workflow et les protections IDOR](docs/etape-11-workflow-idor.md) et [les avis clients](docs/etape-12-avis.md), puis [le centre de notifications](docs/etape-13-notifications.md) et [le Web Push](docs/etape-14-web-push.md), puis [le SMS/OTP professionnel](docs/etape-15-sms-otp.md) et [les plaintes / signalements](docs/etape-16-plaintes.md), puis [les plans et abonnements](docs/etape-17-abonnements.md) et [les paiements sécurisés](docs/etape-18-paiements.md), puis [la PWA et le mode hors connexion](docs/etape-19-pwa-offline.md), puis [l'espace client responsive](docs/etape-20-espace-client.md), puis [l'espace prestataire responsive](docs/etape-21-espace-prestataire.md), puis [l'espace administration responsive](docs/etape-22-espace-administration.md). Sur un poste déjà configuré, depuis la racine du dépôt :

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py check
& ".\.venv\Scripts\python.exe" backend\manage.py test apps.accounts apps.locations apps.catalog apps.providers apps.requests apps.reviews apps.notifications apps.messaging apps.complaints apps.subscriptions apps.payments
git status
```

Ne placez jamais de mots de passe, de clés API, de fichiers `.env` ou de pièces d'identité dans Git. Les migrations applicatives sont versionnées dans le dépôt.

## Docker et Coolify

La stack de production est décrite par `compose.prod.yml` et utilise le nom de projet Docker **`bko_services`**. Son réseau et ses volumes sont donc séparés des autres applications Docker du poste ou du VPS.

Pour un test local Docker sans prendre les ports habituels `3000/8000` :

```powershell
Copy-Item .env.docker.example .env.docker
docker compose --env-file .env.docker -f compose.prod.yml -f compose.local.yml up -d --build
```

Par défaut :

- frontend BKO : `http://localhost:3001` ;
- backend BKO : `http://localhost:8001` ;
- PostgreSQL BKO : réseau Docker interne uniquement, aucun port hôte publié.

Pour arrêter uniquement BKO Services sans toucher à Sugu Kura ou à une autre stack :

```powershell
docker compose --env-file .env.docker -f compose.prod.yml -f compose.local.yml down
```

La procédure complète, les volumes persistants, les variables de production et le futur branchement Coolify sont documentés dans [docs/docker-coolify.md](docs/docker-coolify.md). Le modèle de variables VPS est `.env.production.example`.

## Organisation du travail

Chaque étape suit le cycle : explication → commandes → fichiers complets → vérification → correction → `git status` → commit → push. Les règles de sécurité et les tests sont ajoutés avec les fonctions correspondantes. `main` porte le code stable ; les modifications sont préparées sur des branches `feature/*` ou `fix/*`, puis intégrées par pull request.

## À venir

L'étape 23 dispose maintenant d'une suite de **150 tests sur PostgreSQL**, sans test ignoré. Les tests couvrent notamment le matching quartier → commune → déplacement autorisé, le refus d'un déplacement non autorisé, la relance après ajout d'une commune, l'attribution unique et l'administration sécurisée des catégories/métiers. Les essais mobiles et d'accessibilité restent à consigner : [commandes et résultats](docs/etape-23-qualite.md).

Le [workflow CI](docs/etape-24-ci.md) exécute les contrôles **Backend PostgreSQL**, **Frontend lint and build** et désormais un **Docker production stack** qui construit et démarre les conteneurs puis vérifie les health checks. La prochaine étape technique reste la validation locale de cette stack, puis la préproduction et le déploiement. Voir la [feuille de route de production](docs/production-roadmap.md), le [guide Docker/Coolify](docs/docker-coolify.md) et les [exigences d'architecture](docs/architecture.md).
