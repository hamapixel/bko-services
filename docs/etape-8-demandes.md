# Étape 8 — Création et consultation des demandes

Un compte `CLIENT` au téléphone vérifié peut enregistrer une demande pour un métier actif et un quartier actif. Il renseigne un titre, une description, une adresse précise et une priorité `NORMAL` ou `URGENT`. Le serveur fixe le client à partir de la session, le statut à `CREATED` et inscrit la première ligne d'historique dans la **même transaction**. Il refuse tout champ inattendu, notamment un statut, un prix ou un autre client fourni par le navigateur.

`CREATED` signifie que la demande est enregistrée sur le serveur. **Aucune recherche de prestataire, offre ou notification n'est encore déclenchée** à cette étape, même pour une demande urgente. Le matching et les transitions arriveront aux étapes suivantes ; ne pas présenter `CREATED` comme une attribution effectuée. L'adresse détaillée est visible uniquement par le client propriétaire dans l'API actuelle et par l'administration technique habilitée. Une future offre à un prestataire ne devra pas divulguer l'adresse ni le téléphone du client avant attribution.

| Méthode | Route | Accès |
| --- | --- | --- |
| GET | `/api/v1/requests/` | Liste paginée des demandes du client connecté |
| POST | `/api/v1/requests/` | Crée une demande ; session et jeton CSRF obligatoires |
| GET | `/api/v1/requests/<uuid>/` | Détail et historique de **sa** demande |

Un autre compte, même authentifié, reçoit `404` pour l'UUID d'une demande qui ne lui appartient pas. Aucun endpoint public ne permet de modifier le statut, le prix ou l'historique. La création est limitée en développement à dix demandes par heure et par compte via le cache DRF ; un rate limiting partagé sera nécessaire avant ouverture publique.

## Vérification sous Windows

Depuis la racine du dépôt après avoir récupéré `feature/service-requests` :

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py check
& ".\.venv\Scripts\python.exe" backend\manage.py test apps.accounts apps.locations apps.catalog apps.providers apps.requests --settings=config.test_settings
& ".\.venv\Scripts\python.exe" backend\manage.py migrate --plan
```

Le plan doit seulement prévoir `requests.0001_initial`. Après avoir vérifié ce plan :

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py migrate --noinput
& ".\.venv\Scripts\python.exe" backend\manage.py showmigrations requests
& ".\.venv\Scripts\python.exe" backend\manage.py shell -c "from apps.requests.models import ServiceRequest; print('Demandes :', ServiceRequest.objects.count())"
git status
```

Résultat attendu sur une base vide de demandes : `[X] 0001_initial`, puis `Demandes : 0`. Les tests isolés utilisent SQLite en mémoire et ne modifient pas la base PostgreSQL locale.
