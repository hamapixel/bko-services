# Étape 23 — Qualité avant la préparation serveur

État au 29 septembre 2026 : la suite complète a été vérifiée sur PostgreSQL local avec **141 tests réussis, sans test ignoré**. Les contrôles Django et migrations sont propres (`manage.py check` sans erreur, `makemigrations --check --dry-run` sans changement). Un lot ciblé de **21 tests** couvre les lieux, le matching, les demandes dans des zones non encore répertoriées et l'acceptation PostgreSQL à attributaire unique.

Le frontend a également passé ESLint, TypeScript (`npx tsc --noEmit`) et le build Next.js de production. Les essais mobiles et d'accessibilité restent à consigner avant de clôturer formellement l'étape 23.

## Vérification locale avec PostgreSQL sur Windows

Exécuter depuis la racine `C:\Users\HP USER\bko-services`. Vérifier que le service PostgreSQL est démarré et que le `.env` local pointe vers une **base de développement**, jamais vers une base de production. Django crée une base temporaire de test distincte (par défaut un nom préfixé `test_`) ; le compte PostgreSQL utilisé par Django doit pouvoir créer cette base pendant les tests.

```powershell
git status
& ".\.venv\Scripts\python.exe" backend\manage.py check
& ".\.venv\Scripts\python.exe" backend\manage.py makemigrations --check --dry-run
& ".\.venv\Scripts\python.exe" backend\manage.py test apps.locations apps.requests.test_matching apps.requests.test_unlisted_location apps.requests.test_acceptance_postgres
```

Dernière exécution ciblée : `Found 21 test(s)` puis `Ran 21 tests in 15.820s`, `OK`.

Le lot vérifie notamment :

- la hiérarchie région/district → ville → commune → quartier ;
- les demandes saisies dans une région dont les subdivisions ne sont pas encore référencées ;
- le matching sur le même métier avec priorité au quartier et ouverture à un autre quartier de la même commune ;
- l'acceptation atomique PostgreSQL, qui ne laisse qu'un seul prestataire devenir attributaire.

Si cette vérification passe, lancer la suite complète sur le même moteur :

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py test apps.accounts apps.locations apps.catalog apps.providers apps.requests apps.reviews apps.notifications apps.messaging apps.complaints apps.subscriptions apps.payments
cd frontend
npm.cmd run lint
npx.cmd tsc --noEmit
npm.cmd run build
cd ..
git status
```

Dernière exécution complète locale : `Found 141 test(s)`, `Ran 141 tests in 131.172s`, `OK`, puis destruction normale de la base de test. Les messages `Bad Request`, `Forbidden` ou `Too Many Requests` visibles pendant la suite correspondent à des scénarios de sécurité attendus lorsque le résultat final est `OK`.

Les tests utilisent des doubles pour les fournisseurs externes : ils ne prouvent pas encore qu'un paiement marchand réel, un SMS réel ou une notification Web Push fonctionne en production.

## Droit PostgreSQL de création de base

Si Django affiche `droit refusé pour créer une base de données`, accorder temporairement `CREATEDB` au rôle de développement, par exemple :

```powershell
psql -U postgres -d postgres -c "ALTER ROLE bko_services_user CREATEDB;"
```

Après les campagnes locales, ce droit peut être retiré pour revenir au moindre privilège :

```powershell
psql -U postgres -d postgres -c "ALTER ROLE bko_services_user NOCREATEDB;"
```

Ne jamais appliquer ces commandes à un compte de production sans procédure d'administration dédiée.

## Passage de l'étape

- Validé : 141 tests backend sur PostgreSQL, sans test ignoré.
- Validé : 21 tests ciblés sur lieux, matching, zones non répertoriées et acceptation atomique.
- Validé : `check` Django et absence de migration inattendue.
- Validé : ESLint, TypeScript et build Next.js.
- À consigner : essais manuels iPhone/Android/tablette, clavier, focus, formulaires, erreurs, navigation et installation PWA.
- À consigner : vérification d'accessibilité pratique (navigation clavier, focus visible, libellés, contrastes et réduction des animations).

Les protections d'accès croisé restent obligatoires : un autre prestataire ne peut pas lire une offre ou une intervention qui ne lui appartient pas, et un autre client ne peut pas consulter ou noter une demande étrangère.
