# Étape 23 — Qualité avant la préparation serveur

État au 26 septembre 2026 : le parcours API client → prestataire → avis et notification a été ajouté. Le modèle `PasswordResetCode` porte le nom d'index déjà présent dans sa migration ; `makemigrations --check --dry-run` ne demande plus de renommage. La suite SQLite passe **130 tests, dont 2 ignorés car ils exigent PostgreSQL**. Sur le poste Windows de développement, PostgreSQL 18.4 a exécuté **130 tests avec résultat OK, sans test ignoré** ; les 3 tests ciblés de concurrence et de parcours ont également réussi.

## Vérification locale avec PostgreSQL sur Windows

Exécuter depuis la racine `C:\Users\HP USER\bko-services`, sur la branche `fix/regions-auto-matching`. Vérifier que le service PostgreSQL est démarré et que le `.env` local pointe vers une **base de développement**, jamais vers une base de production. Django crée une base temporaire de test distincte (par défaut un nom préfixé `test_`) ; le compte PostgreSQL doit avoir le droit de la créer. Ne pas supprimer manuellement une base existante qui contient des données utiles.

```powershell
git pull --ff-only origin fix/regions-auto-matching
& ".\.venv\Scripts\python.exe" backend\manage.py check
& ".\.venv\Scripts\python.exe" backend\manage.py makemigrations --check --dry-run
& ".\.venv\Scripts\python.exe" backend\manage.py test apps.requests.test_acceptance_postgres apps.requests.test_journey
```

Le premier module lance deux tests **réellement PostgreSQL** : deux prestataires acceptent la même demande en parallèle, puis une intervention progresse jusqu'à l'avis. Le second traverse les vraies API de création, offre, acceptation, intervention, confirmation et avis ; il vérifie aussi la confidentialité de l'offre et la notification. Les trois tests ont réussi, **sans mention `skipped`**.

Si cette vérification passe, lancer la suite complète sur le même moteur :

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py test apps.accounts apps.locations apps.catalog apps.providers apps.requests apps.reviews apps.notifications apps.messaging apps.complaints apps.subscriptions apps.payments
cd frontend
npm.cmd run lint
npm.cmd run build
```

Exécution du 26 septembre : `Ran 130 tests in 88.687s`, `OK`, base de test détruite. Le droit PostgreSQL temporaire `CREATEDB` a été retiré après le test (`rolcreatedb = f`). Les refus CSRF, codes 400 et limite de requêtes affichés pendant la suite proviennent des scénarios de sécurité attendus. Les tests utilisent des doubles pour les fournisseurs externes : ils ne valident pas encore un vrai paiement marchand ou un SMS livré.

La dernière vérification du frontend a réussi dans l'environnement de développement de la branche. Le contrôle `check --deploy` avec des valeurs de test signale encore HSTS, redirection HTTPS et clé de test courte : ce sont des réglages à valider sur la configuration de l'étape 25, avec le reverse proxy HTTPS retenu.

## Passage de l'étape

- Terminé : les 130 tests passent sur PostgreSQL, dont les deux tests spécifiques de concurrence et de progression ; aucune migration inattendue dans le dernier contrôle.
- Un test manuel sur mobile vérifie les formulaires, les boutons, le clavier, les états d'erreur et les barres de navigation client, prestataire et admin, à largeur iPhone et tablette. Vérifier également la commande clavier et le focus de la fenêtre d'installation PWA.
- Les tests d'accès croisé sont conservés : un autre prestataire ne peut pas lire une offre ou une intervention, et un autre client ne peut pas voir ou noter la demande.
- À faire : consigner les essais mobiles et d'accessibilité avant de clôturer l'étape 23. La CI PostgreSQL est prévue à l'étape 24.
