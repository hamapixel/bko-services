# Docker et déploiement Coolify — BKO Services

## Isolation avec les autres projets Docker

BKO Services utilise le nom de projet Compose `bko_services`.

Cela isole automatiquement :

- le réseau Docker (`bko_services_internal`) ;
- le volume PostgreSQL (`bko_services_postgres_data`) ;
- le volume des médias (`bko_services_media_data`) ;
- les conteneurs générés par Compose.

Aucun `container_name` global n'est imposé et PostgreSQL n'est pas publié sur un port de la machine hôte.

Le fichier de production `compose.prod.yml` n'ouvre aucun port hôte fixe. Pour le test local, `compose.local.yml` publie uniquement :

- frontend BKO : `localhost:3001` -> conteneur `3000` ;
- backend BKO : `localhost:8001` -> conteneur `8000`.

Ces valeurs peuvent être changées dans `.env.docker` si un autre projet utilise déjà ces ports.

## Test local sur Windows

Depuis la racine du dépôt :

```powershell
Copy-Item .env.docker.example .env.docker
```

Vérifier la configuration sans démarrer :

```powershell
docker compose --env-file .env.docker -f compose.prod.yml -f compose.local.yml config
```

Construire et démarrer uniquement BKO Services :

```powershell
docker compose --env-file .env.docker -f compose.prod.yml -f compose.local.yml up -d --build
```

État des services :

```powershell
docker compose --env-file .env.docker -f compose.prod.yml -f compose.local.yml ps
```

URLs locales :

- application : `http://localhost:3001`
- health backend : `http://localhost:8001/health/`

Afficher les logs BKO uniquement :

```powershell
docker compose --env-file .env.docker -f compose.prod.yml -f compose.local.yml logs -f
```

Arrêter BKO sans toucher aux autres projets Docker :

```powershell
docker compose --env-file .env.docker -f compose.prod.yml -f compose.local.yml down
```

Ne pas ajouter `-v` si vous voulez conserver la base PostgreSQL et les médias BKO.

## Services de la stack

### `db`

PostgreSQL 18 avec volume persistant. Il est accessible seulement depuis le réseau interne BKO.

### `backend`

Django est servi par Gunicorn. Au démarrage, l'entrypoint :

1. attend que PostgreSQL soit sain via `depends_on` ;
2. applique les migrations si `RUN_MIGRATIONS=true` ;
3. exécute `collectstatic` ;
4. lance Gunicorn sur le port interne `8000`.

Les fichiers médias (par exemple les avatars) sont conservés dans un volume Docker persistant.

### `frontend`

Next.js est construit en mode `standalone` et écoute sur le port interne `3000`.

Le proxy Next.js transmet `/api/...` vers le service Docker interne `backend:8000`, donc le navigateur reste sur le même domaine public.

## Déploiement futur avec Coolify

Quand le VPS sera prêt :

1. installer Coolify sur le VPS ;
2. connecter le dépôt GitHub `hamapixel/bko-services` ;
3. créer une ressource Docker Compose à partir de `compose.prod.yml` ;
4. ajouter dans Coolify les variables indiquées dans `.env.production.example` ;
5. remplacer `bko.example.com` par le vrai domaine ;
6. associer le domaine public au service `frontend`, port interne `3000` ;
7. laisser `db` non public ;
8. conserver les volumes PostgreSQL et médias comme volumes persistants ;
9. vérifier `/health/`, les connexions, les uploads, les notifications et les paiements ;
10. activer HSTS seulement après validation complète de HTTPS.

Le backend n'a pas besoin d'un port public pour le fonctionnement normal du frontend : les appels `/api` passent par Next.js vers le réseau Docker interne.

## Variables sensibles

Ne jamais committer les vraies valeurs de :

- `DJANGO_SECRET_KEY` ;
- `POSTGRES_PASSWORD` ;
- clés VAPID privées ;
- identifiants SMS/Twilio ;
- clés Wave ;
- secrets de webhook.

`.env.docker` et `.env.production` sont ignorés par Git. Seuls les fichiers `*.example` sont versionnés.

## Sauvegardes

Avant la mise en production publique, prévoir :

- sauvegarde régulière PostgreSQL ;
- sauvegarde du volume médias ;
- test de restauration ;
- conservation d'au moins une copie hors du VPS.
