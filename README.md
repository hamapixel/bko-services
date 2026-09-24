# BKO Services

**Le bon professionnel, au bon moment.** BKO Services met en relation des clients et des professionnels de proximité à Bamako. Le premier parcours à livrer couvre l'inscription, le choix d'un métier et d'un quartier, la création d'une demande, l'attribution à un professionnel, le suivi de l'intervention et l'avis du client.

> Statut : **étape 22 — espace administration responsive validé localement**. Dashboard permission-aware, prestataires, demandes, plaintes, abonnements, paiements et utilisateurs sont branchés sur les API Django sécurisées.

## Principes

- Les clients n'accéderont qu'à leurs demandes ; les professionnels n'accéderont qu'aux offres qui leur sont adressées et aux interventions qui leur sont attribuées. Ces règles seront appliquées dans l'API et testées contre les accès par identifiant (IDOR).
- Une demande urgente pourra être proposée à cinq professionnels compatibles au maximum. Une transaction PostgreSQL garantit qu'un seul l'accepte.
- Les pièces d'identité et les coordonnées privées devront rester protégées. Avant attribution, l'offre transmise au professionnel contient seulement les renseignements nécessaires pour décider.
- L'interface mobile devra rester utilisable avec une connexion instable. Une demande conservée hors connexion sera clairement marquée **non envoyée** jusqu'à confirmation du serveur.
- Les prestataires devront être vérifiés pour recevoir des demandes. Les tarifs, catégories et quartiers seront gérés côté serveur.

## Architecture retenue

| Composant | Choix | Responsabilité |
| --- | --- | --- |
| API | Django + Django REST Framework | Authentification, droits d'accès, règles métier, administration et API `/api/v1/` |
| Données | PostgreSQL | Données relationnelles, contraintes et attribution atomique |
| Application web | Une application Next.js + TypeScript | Pages publiques et espaces client, prestataire et administrateur ; PWA responsive |
| Tâches | Celery + Redis | Notifications, SMS, rappels et expirations hors des requêtes HTTP |
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

Le choix suit désormais **région ou district → ville → commune → quartier**. Pour le périmètre actuel, le District de Bamako contient la ville de Bamako et les communes/quartiers déjà chargés. Les autres régions et villes peuvent être ajoutées depuis l'administration avant d'être proposées aux clients. Une migration rattache la ville de Bamako déjà présente à son district ; les villes créées manuellement doivent être rattachées à une région ou un district.

Lorsqu'un client vérifié envoie une demande, le serveur lance immédiatement la recherche et crée une offre privée pour un prestataire compatible (jusqu'à cinq pour une urgence). La correspondance nécessite le **même métier et le même quartier desservi** ; le prestataire doit être approuvé, disponible, actif, avoir son téléphone vérifié et un abonnement autorisant ce type de demande. Sans candidat, la demande reste « Recherche en cours » et l'administrateur peut relancer le matching depuis `/admin/demandes` lorsque le prestataire est prêt. Les demandes créées avant cette modification nécessitent également cette relance manuelle.

## Démarrage sur Windows

Après avoir cloné le dépôt, consulter [l'installation du backend et du frontend](docs/etape-2.md), [le modèle utilisateur](docs/etape-3.md), [l'authentification](docs/etape-4-auth.md), [les lieux](docs/etape-5-lieux.md), [le catalogue](docs/etape-6-catalogue.md), [les prestataires](docs/etape-7-prestataires.md), [les demandes](docs/etape-8-demandes.md), [le matching](docs/etape-9-matching.md) et [l'acceptation atomique](docs/etape-10-acceptation.md), puis [le workflow et les protections IDOR](docs/etape-11-workflow-idor.md) et [les avis clients](docs/etape-12-avis.md), puis [le centre de notifications](docs/etape-13-notifications.md) et [le Web Push](docs/etape-14-web-push.md), puis [le SMS/OTP professionnel](docs/etape-15-sms-otp.md) et [les plaintes / signalements](docs/etape-16-plaintes.md), puis [les plans et abonnements](docs/etape-17-abonnements.md) et [les paiements sécurisés](docs/etape-18-paiements.md), puis [la PWA et le mode hors connexion](docs/etape-19-pwa-offline.md), puis [l'espace client responsive](docs/etape-20-espace-client.md), puis [l'espace prestataire responsive](docs/etape-21-espace-prestataire.md), puis [l'espace administration responsive](docs/etape-22-espace-administration.md). Sur un poste déjà configuré, depuis la racine du dépôt :

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py check
& ".\.venv\Scripts\python.exe" backend\manage.py test apps.accounts apps.locations apps.catalog apps.providers apps.requests apps.reviews apps.notifications apps.messaging apps.complaints apps.subscriptions apps.payments --settings=config.test_settings
git status
```

Ne placez jamais de mots de passe, de clés API, de fichiers `.env` ou de pièces d'identité dans Git. Les migrations applicatives sont versionnées dans le dépôt.

## Organisation du travail

Chaque étape suit le cycle : explication → commandes → fichiers complets → vérification → correction → `git status` → commit → push. Les règles de sécurité et les tests sont ajoutés avec les fonctions correspondantes. `main` porte le code stable ; les modifications sont préparées sur des branches `feature/*`.

## À venir

Tests renforcés, CI, Docker et déploiement. Les exigences avant production figurent dans [docs/architecture.md](docs/architecture.md).
