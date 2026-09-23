# BKO Services

**Le bon professionnel, au bon moment.** BKO Services met en relation des clients et des professionnels de proximité à Bamako. Le premier parcours à livrer couvre l'inscription, le choix d'un métier et d'un quartier, la création d'une demande, l'attribution à un professionnel, le suivi de l'intervention et l'avis du client.

> Statut : **étape 0 — cadrage**. Le dépôt ne contient pas encore d'application exécutable. Aucun modèle Django, projet Next.js ou migration n'a été créé.

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
- [ ] Étape 1 : environnement de développement Windows et vérification des outils.
- [ ] Étape 2 : création du backend et du frontend.
- [ ] Étapes suivantes : développement incrémental selon la feuille de route.

## Démarrage sur Windows

Les commandes d'installation arriveront à l'étape 1 après vérification de Git, Python, Node.js et PostgreSQL. Pour récupérer ce cadrage dès maintenant :

```powershell
git clone https://github.com/hamapixel/bko-services.git
cd bko-services
git status
```

Ne placez jamais de mots de passe, de clés API, de fichiers `.env` ou de pièces d'identité dans Git. Les migrations applicatives seront versionnées lorsqu'elles seront créées.

## Organisation du travail

Chaque étape suit le cycle : explication → commandes → fichiers complets → vérification → correction → `git status` → commit → push. Les règles de sécurité et les tests sont ajoutés avec les fonctions correspondantes. `main` porte le code stable ; `develop` et les branches `feature/*` seront créées au moment utile.

## À venir

Installation locale, API documentée avec OpenAPI, tests backend/frontend, PWA, sauvegardes, restauration, CI et déploiement. Les exigences avant production figurent dans [docs/architecture.md](docs/architecture.md).
