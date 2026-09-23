# Étape 3 — Custom User avant la première migration

`accounts.User` remplace l'utilisateur Django par défaut. Son identifiant est un UUID et la connexion utilise un numéro au format international (`+223` suivi de huit chiffres au Mali). Le rôle initial est `CLIENT` ; un superutilisateur créé avec `createsuperuser` reçoit `SUPERADMIN`.

Les quatre rôles sont `CLIENT`, `PROVIDER`, `ADMIN`, `SUPERADMIN`. Le champ `role` ne doit **jamais** être modifiable par les API de profil : ce contrôle sera appliqué lors de la création des serializers et endpoints à l'étape 4. `phone_verified_at` reste vide tant que l'OTP n'a pas été vérifié.

## À vérifier avant de migrer

Il ne doit pas y avoir de table `django_migrations` dans `bko_services_db`. Depuis PowerShell à la racine du projet :

```powershell
psql -h localhost -U bko_services_user -d bko_services_db -c "SELECT to_regclass('public.django_migrations') AS migration_table;"
```

La cellule `migration_table` doit être vide. Si une table existe, **arrêter ici** et faire examiner la base avant de poursuivre. Ne pas supprimer de tables à l'aveugle.

## Appliquer la première migration

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py check
& ".\.venv\Scripts\python.exe" backend\manage.py migrate --plan
& ".\.venv\Scripts\python.exe" backend\manage.py migrate --noinput
& ".\.venv\Scripts\python.exe" backend\manage.py showmigrations accounts
& ".\.venv\Scripts\python.exe" backend\manage.py shell -c "from django.contrib.auth import get_user_model; u=get_user_model(); print(u._meta.label, u.USERNAME_FIELD, u._meta.pk.get_internal_type())"
```

Résultats attendus : aucune erreur au `check`, migration `accounts.0001_initial` marquée `[X]`, puis `accounts.User phone UUIDField`. La commande `migrate` applique également les migrations Django nécessaires (`auth`, `admin`, `contenttypes`, `sessions`).

## Accès administrateur local (après migration seulement)

Un superadministrateur peut ensuite être créé avec :

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py createsuperuser
```

Saisir son téléphone sous la forme `+223XXXXXXXX` et choisir un mot de passe robuste sans le partager. L'administration technique sera accessible sur `/django-admin/` lorsque le serveur de développement sera démarré. Les comptes clients et prestataires seront créés par des parcours contrôlés aux étapes suivantes.
