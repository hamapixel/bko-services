# Étape 10 — Acceptation atomique et attribution unique

L'étape 10 ajoute l'acceptation d'une offre par son prestataire destinataire. La route est :

| Méthode | Route | Accès |
| --- | --- | --- |
| POST | `/api/v1/providers/offers/<uuid>/accept/` | Prestataire destinataire authentifié |

## Règles métier

L'acceptation est exécutée dans une transaction. La ligne `ServiceRequest` est verrouillée avec `select_for_update()` avant la décision finale. Le serveur revérifie ensuite que :

- la demande est toujours `OFFERED` et n'a aucun prestataire attribué ;
- l'offre appartient bien au prestataire et est encore `PENDING` ;
- le compte est actif, de rôle `PROVIDER` et le téléphone reste vérifié ;
- le profil reste `VERIFIED` et disponible ;
- le métier, sa catégorie, le quartier, la commune et la ville restent actifs ;
- le prestataire possède toujours le métier demandé et dessert toujours le quartier.

Le gagnant devient `assigned_provider`, la demande passe à `ACCEPTED`, son offre passe à `ACCEPTED`, et les autres offres encore en attente passent à `CANCELLED`. L'historique enregistre `OFFERED → ACCEPTED`.

La base ajoute aussi la contrainte conditionnelle `requests_one_accepted_offer`, qui interdit plusieurs offres `ACCEPTED` pour une même demande. Elle complète le verrou transactionnel.

## Concurrence PostgreSQL

Le test `test_acceptance_postgres.py` lance deux transactions réelles qui tentent d'accepter deux offres de la même demande. PostgreSQL doit produire exactement un gagnant et un refus.

## Vérification sous Windows

Après récupération de la branche :

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py check
& ".\.venv\Scripts\python.exe" backend\manage.py migrate --plan
& ".\.venv\Scripts\python.exe" backend\manage.py test apps.accounts apps.locations apps.catalog apps.providers apps.requests --settings=config.test_settings
```

Le test isolé SQLite valide les règles métier et la contrainte. Le test de concurrence doit ensuite être exécuté avec les paramètres PostgreSQL du projet :

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py test apps.requests.test_acceptance_postgres
```

Après validation, appliquer la migration locale puis vérifier son état.
