# Étape 24 — Contrôles automatiques

Le workflow [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) s'exécute sur les pull requests, les changements sur `main` et à la demande. Les deux contrôles sont séparés : **Backend PostgreSQL** et **Frontend lint and build**.

- Le backend installe les dépendances Python, vérifie Django et les migrations, puis exécute la suite complète sur un service PostgreSQL 18 temporaire.
- Le frontend utilise Node.js 24 et `npm ci` à partir du lockfile, puis lance ESLint, TypeScript et le build Next.js.
- Le jeton GitHub a seulement le droit de lire le dépôt. Les contrôles ne publient pas d'artefact et ne déploient pas l'application.

Sur la branche de préparation du matching inter-commune, le job backend a validé `manage.py check`, `makemigrations --check --dry-run` et **146 tests PostgreSQL réussis**. Toute modification ultérieure d'une pull request relance la CI et doit à nouveau obtenir les deux checks verts avant intégration. Un check vert sur un ancien commit ne remplace jamais la validation du head actuel de la PR.

## Protection de `main`

Le ruleset GitHub `main` est **Active** et cible la branche par défaut. Il impose :

- une pull request avant fusion ;
- zéro approbation obligatoire pour permettre une gestion individuelle du dépôt ;
- les checks requis **Backend PostgreSQL** et **Frontend lint and build** ;
- l'interdiction de supprimer `main` ;
- l'interdiction des mises à jour non fast-forward ;
- aucun acteur de contournement configuré.

Les méthodes de fusion autorisées par la règle sont merge, squash et rebase. Pour une branche fonctionnelle importante, conserver une PR explicite vers `main` permet d'avoir un historique de validation lisible et de laisser les checks requis protéger la livraison.

## État de passage

- CI backend PostgreSQL : opérationnelle ; état courant de la suite fonctionnelle, **146 tests**.
- CI frontend ESLint + TypeScript + build : opérationnelle et obligatoire avant fusion.
- Ruleset `main` : actif avec pull request et deux checks requis.
- Déploiement automatique : non configuré, volontairement reporté aux étapes serveur/préproduction.
- Prochaine étape : préparation serveur et paramètres de production, après validation de la PR fonctionnelle en cours et clôture des essais mobiles/accessibilité de l'étape 23.
