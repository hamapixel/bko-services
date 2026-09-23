# BKO Services

**Le bon professionnel, au bon moment.** BKO Services met en relation des clients et des professionnels de proximité à Bamako. Le premier parcours à livrer couvre l'inscription, le choix d'un métier et d'un quartier, la création d'une demande, l'attribution à un professionnel, le suivi de l'intervention et l'avis du client.

> Statut : **étape 6 — catégories et métiers administrables validés sur PostgreSQL local**. L'API Django, le frontend Next.js et les migrations du compte utilisateur, des lieux et du catalogue sont présents. L'envoi de SMS réel sera intégré à l'étape 15.

## Principes

- Les clients n'accéderont qu'à leurs demandes ; les professionnels n'accéderont qu'aux offres qui leur sont adressées et aux interventions qui leur sont attribuées. Ces règles seront appliquées dans l'API et testées contre les accès par identifiant (IDOR).
- Une demande urgente pourra être proposée à cinq professionnels compatibles au maximum. Une transaction PostgreSQL garantira qu'un seul l'accepte.
- Les pièces d'identité et les coordonnées privées devront rester protégées. Avant attribution, l'offre transmise au professionnel contiendra seulement les renseignements nécessaires pour décider.
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
- [ ] Étape 7 : profils et vérification des prestataires.

## Démarrage sur Windows

Après avoir cloné le dépôt, consulter [l'installation du backend et du frontend](docs/etape-2.md), [le modèle utilisateur](docs/etape-3.md) et [l'authentification](docs/etape-4-auth.md), [les lieux](docs/etape-5-lieux.md) et [le catalogue](docs/etape-6-catalogue.md). Sur un poste déjà configuré, depuis la racine du dépôt :

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py check
& ".\.venv\Scripts\python.exe" backend\manage.py test apps.accounts apps.locations apps.catalog --settings=config.test_settings
git status
```

Ne placez jamais de mots de passe, de clés API, de fichiers `.env` ou de pièces d'identité dans Git. Les migrations applicatives sont versionnées dans le dépôt.

## Organisation du travail

Chaque étape suit le cycle : explication → commandes → fichiers complets → vérification → correction → `git status` → commit → push. Les règles de sécurité et les tests sont ajoutés avec les fonctions correspondantes. `main` porte le code stable ; les modifications sont préparées sur des branches `feature/*`.

## À venir

Prestataires, demandes, API documentée avec OpenAPI, PWA, sauvegardes, restauration, CI et déploiement. Les exigences avant production figurent dans [docs/architecture.md](docs/architecture.md).
