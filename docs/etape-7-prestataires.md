# Étape 7 — Candidatures et vérification des prestataires

Un compte `CLIENT` avec téléphone vérifié peut déposer **une seule** candidature. Le dossier contient un nom légal réservé au candidat et à l'administration, un nom public, une description, des métiers actifs et des quartiers actifs. L'inscription ne donne aucun privilège de prestataire : le rôle reste `CLIENT` et le statut `PENDING`.

L'administrateur vérifie l'identité **hors ligne**, sans enregistrer de photo de pièce d'identité dans ce module. Dans `/django-admin/`, il coche « identity checked », écrit une note de contrôle **sans numéro de pièce ni donnée sensible**, enregistre le dossier, puis utilise l'action « Approuver après contrôle d'identité ». L'approbation vérifie de nouveau le téléphone, les métiers et quartiers actifs, passe le statut à `VERIFIED` et donne le rôle `PROVIDER` dans une transaction. Une note est aussi obligatoire pour refuser, suspendre ou rouvrir un dossier. Chaque décision crée un historique privé. Seuls les superadministrateurs et les administrateurs explicitement habilités peuvent utiliser ces actions.

Les candidats peuvent corriger un dossier `PENDING` ou `REJECTED`. Toute modification annule la confirmation d'identité précédente ; un dossier refusé repasse en attente. Une modification du dossier dans l'administration annule également ce contrôle. Un dossier vérifié ou suspendu ne peut pas être modifié par le candidat. Une suspension retire le rôle de prestataire et désactive sa disponibilité. La disponibilité ne peut être activée qu'avec un téléphone, un métier et une zone actifs. La future attribution des demandes devra revérifier ces conditions dans une transaction.

| Méthode | Route | Accès |
| --- | --- | --- |
| POST, GET, PATCH | `/api/v1/providers/application/` | Dossier du compte connecté |
| PATCH | `/api/v1/providers/availability/` | Disponibilité du prestataire vérifié |
| GET | `/api/v1/providers/` | Profils vérifiés publiables, paginés |

La liste publique renvoie seulement l'UUID, le nom public, la description et les identifiants des métiers et zones actifs ; ni téléphone, ni nom légal, ni notes d'administration. Les routes d'écriture utilisent la session et un jeton CSRF. L'administration des catégories et quartiers doit avoir été remplie avant de tester une vraie candidature ; aucune candidature factice n'est créée par la migration.

## Vérification sous Windows

Depuis la racine après avoir récupéré `feature/providers` :

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py check
& ".\.venv\Scripts\python.exe" backend\manage.py test apps.accounts apps.locations apps.catalog apps.providers --settings=config.test_settings
& ".\.venv\Scripts\python.exe" backend\manage.py migrate --plan
```

Le plan doit contenir uniquement `providers.0001_initial`. Après avoir vérifié ce plan :

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py migrate --noinput
& ".\.venv\Scripts\python.exe" backend\manage.py showmigrations providers
& ".\.venv\Scripts\python.exe" backend\manage.py shell -c "from apps.providers.models import ProviderProfile; print('Candidatures :', ProviderProfile.objects.count())"
git status
```

Résultat attendu sur une base sans candidatures : `[X] 0001_initial`, puis `Candidatures : 0`. Les tests utilisent SQLite en mémoire et ne modifient pas la base PostgreSQL locale.
