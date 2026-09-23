# BKO Services

**Le bon professionnel, au bon moment.** BKO Services met en relation des clients et des professionnels de proximité à Bamako. Le premier parcours à livrer couvre l'inscription, le choix d'un métier et d'un quartier, la création d'une demande, l'attribution à un professionnel, le suivi de l'intervention et l'avis du client.

> Statut : **étape 1 — environnement Windows vérifié**. Le dépôt ne contient pas encore d'application exécutable. Aucun modèle Django, projet Next.js ou migration n'a été créé.

## Principes

- Les clients n'accèdent qu'à leurs demandes ; les professionnels n'accèdent qu'aux offres qui leur sont adressées et aux interventions qui leur sont attribuées. Ces règles sont appliquées dans l'API et testées contre les accès par identifiant (IDOR).
- Une demande urgente peut être proposée à cinq professionnels compatibles au maximum. Une transaction PostgreSQL garantit qu'un seul l'accepte.
- Les pièces d'identité et les coordonnées privées restent protégées. Avant attribution, l'offre transmise au professionnel contient seulement les renseignements nécessaires pour décider.
- L'interface mobile reste utilisable avec une connexion instable. Une demande conservée hors connexion est clairement marquée **non envoyée** jusqu'à confirmation du serveur.
- Les prestataires doivent être vérifiés pour recevoir des demandes. Les tarifs, catégories et quartiers sont gérés côté serveur.

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
- [x] Étape 1 : Git, Python, Node.js, npm, PostgreSQL et environnement virtuel vérifiés sous Windows.
- [ ] Étape 2 : création du backend et du frontend.
- [ ] Étapes suivantes : développement incrémental selon la feuille de route.

## Démarrage sur Windows

Sur le poste de développement, Git 2.55, Python 3.14.6, Node.js 24.19, npm 11.17 et PostgreSQL 18.4 ont été vérifiés. Le service PostgreSQL tourne et répond sur `localhost:5432`. L'environnement Python local `.venv` fonctionne et est ignoré par Git. Pour installer le dépôt sur un autre poste :

```powershell
git clone https://github.com/hamapixel/bko-services.git
cd bko-services
py -m venv .venv
& ".\.venv\Scripts\python.exe" --version
pg_isready -h localhost -p 5432
git status
```

L'activation PowerShell de `.venv` n'est pas nécessaire : les prochaines commandes peuvent appeler directement `".\.venv\Scripts\python.exe"`. Redis sera installé lorsque les tâches asynchrones seront mises en place. L'étape 2 créera les premiers fichiers du backend et du frontend.

Ne placez jamais de mots de passe, de clés API, de fichiers `.env` ou de pièces d'identité dans Git. Les migrations applicatives seront versionnées lorsqu'elles seront créées.

## Organisation du travail

Chaque étape suit le cycle : explication → commandes → fichiers complets → vérification → correction → `git status` → commit → push. Les règles de sécurité et les tests sont ajoutés avec les fonctions correspondantes. `main` porte le code stable ; `develop` et les branches `feature/*` seront créées au moment utile.

## À venir

Installation locale, API documentée avec OpenAPI, tests backend/frontend, PWA, sauvegardes, restauration, CI et déploiement. Les exigences avant production figurent dans [docs/architecture.md](docs/architecture.md).
