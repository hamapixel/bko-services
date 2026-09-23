# Étape 6 — Catégories et métiers

Une catégorie regroupe des métiers. Par exemple, un administrateur peut créer la catégorie « Maison » puis le métier « Plomberie ». Ces exemples ne sont **pas** ajoutés automatiquement à la base : les intitulés publics doivent être choisis et validés par l'équipe avant publication.

`Category` et `Trade` disposent d'un UUID, d'un nom, d'une description destinée au public, d'un ordre d'affichage et d'un statut actif. Un métier appartient à une catégorie ; supprimer une catégorie ayant des métiers est bloqué par la base (`PROTECT`). Des contraintes en base interdisent deux noms de catégorie équivalents ou deux métiers de même nom dans une catégorie, sans tenir compte des majuscules. Les comptes disposant des permissions d'administration Django gèrent ces données sur `/django-admin/` ; les utilisateurs ne peuvent pas les modifier via l'API publique.

| Méthode | Route | Usage |
| --- | --- | --- |
| GET | `/api/v1/catalog/categories/` | Catégories actives |
| GET | `/api/v1/catalog/trades/?category=<uuid>` | Métiers actifs d'une catégorie active |

Sans paramètre `category`, la liste des métiers affiche ceux de toutes les catégories actives. Les réponses sont paginées par 20 éléments (`count`, `next`, `previous`, `results`) ; un UUID mal formé renvoie `400`. Désactiver une catégorie masque tous ses métiers dans ces listes. Les tarifs et les profils prestataires seront ajoutés aux étapes prévues : aucune donnée tarifaire n'est créée à cette étape.

## Vérification sous Windows

Depuis la racine du dépôt après avoir récupéré `feature/catalog` :

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py check
& ".\.venv\Scripts\python.exe" backend\manage.py test apps.accounts apps.locations apps.catalog --settings=config.test_settings
& ".\.venv\Scripts\python.exe" backend\manage.py migrate --plan
```

Le plan doit prévoir uniquement `catalog.0001_initial` (création des deux modèles). Après vérification :

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py migrate --noinput
& ".\.venv\Scripts\python.exe" backend\manage.py showmigrations catalog
& ".\.venv\Scripts\python.exe" backend\manage.py shell -c "from apps.catalog.models import Category, Trade; print('Catégories :', Category.objects.count(), 'Métiers :', Trade.objects.count())"
git status
```

Résultats attendus avant tout ajout dans l'administration : `[X] 0001_initial`, puis `Catégories : 0 Métiers : 0`. Les tests utilisent SQLite en mémoire et ne touchent pas à votre base PostgreSQL.
