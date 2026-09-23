# Étape 2 — Squelette backend et frontend

Cette branche contient le socle Django/DRF et une page d'accueil Next.js. Elle ne contient **aucun modèle métier ni migration ajoutée au projet**. Ne pas exécuter `migrate` avant l'étape 3 (Custom User).

## Préparer le backend sous Windows

Depuis la racine de `bko-services` dans PowerShell :

```powershell
& ".\.venv\Scripts\python.exe" -m pip install -r backend\requirements.txt
Copy-Item .env.example .env
& ".\.venv\Scripts\python.exe" -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
notepad .env
```

Dans `.env`, coller la clé générée après `DJANGO_SECRET_KEY=` et renseigner le mot de passe du rôle `bko_services_user` après `DB_PASSWORD=`. Ne publier ni la clé ni le mot de passe. Si le mot de passe contient un espace ou un `#`, entourer sa valeur de guillemets dans `.env`. Garder `DJANGO_DEBUG=True` uniquement sur le poste local.

Vérifier Django et la connexion PostgreSQL :

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py check
& ".\.venv\Scripts\python.exe" backend\manage.py shell -c "from django.db import connection; connection.ensure_connection(); print('PostgreSQL OK')"
& ".\.venv\Scripts\python.exe" backend\manage.py shell -c "from django.test import Client; print(Client(HTTP_HOST='localhost').get('/health/').json())"
```

La réponse attendue est `System check identified no issues`, puis `PostgreSQL OK`, puis `{'status': 'ok', 'service': 'bko-services-api'}`. La page `/api/v1/health/` répond également sans authentification. Les autres endpoints ne sont pas encore implémentés.

## Vérifier le frontend

Dans le même terminal, après les vérifications backend :

```powershell
cd frontend
npm.cmd ci
npm.cmd run lint
npm.cmd run build
cd ..
git status
```

Pour voir l'accueil, lancer `npm.cmd run dev` dans `frontend` et ouvrir `http://localhost:3000`. Le frontend ne communique pas encore avec l'API. La PWA, les comptes et les formulaires arriveront aux étapes prévues.

## Étape suivante

À l'étape 3, créer `apps.accounts.User`, déclarer `AUTH_USER_MODEL`, puis seulement produire et appliquer les premières migrations. Tant que l'étape 3 n'est pas finie, **ne pas exécuter** `python backend\manage.py migrate` ni `makemigrations`.
