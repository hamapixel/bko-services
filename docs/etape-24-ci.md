# Étape 24 — Contrôles automatiques

Le workflow [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) s'exécute sur les pull requests, les changements sur `main` et à la demande. Les deux contrôles sont séparés : **Backend PostgreSQL** et **Frontend lint and build**.

- Le backend installe les dépendances Python, vérifie Django et les migrations, puis exécute les 130 tests sur un service PostgreSQL 18 temporaire. Les valeurs de connexion et la clé Django dans le workflow sont uniquement des données de test ; aucun compte marchand, mot de passe de production ou secret GitHub n'est nécessaire.
- Le frontend utilise Node.js 24 et `npm ci` à partir du lockfile, puis lance ESLint, TypeScript et le build Next.js.
- Le jeton GitHub a seulement le droit de lire le dépôt. Les contrôles ne publient pas d'artefact et ne déploient pas l'application.

Après publication, ouvrir la PR #22 et attendre les deux contrôles. Si un contrôle échoue, corriger sa cause puis vérifier le nouveau passage. Les tests PostgreSQL locaux du 26 septembre étaient verts (130 tests, aucun ignoré) ; cela ne vaut pas encore un résultat CI.

Pour empêcher une fusion en cas d'échec, activer dans les paramètres GitHub de `main` une règle demandant une pull request et les contrôles **Backend PostgreSQL** et **Frontend lint and build**. Sélectionner les noms réellement affichés dans la PR après le premier passage du workflow. Ne pas imposer une règle avant leur première exécution, car GitHub ne peut pas proposer un contrôle qui n'existe pas encore.

Les essais visuels et d'accessibilité sur téléphone et tablette restent à consigner au titre de l'étape 23. L'étape 25 concernera la configuration serveur et les secrets réels.
