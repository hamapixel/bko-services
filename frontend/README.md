# Frontend BKO Services

Frontend Next.js App Router, TypeScript et Tailwind CSS.

L'étape 20 livre le premier espace métier complet : l'espace client responsive.

## Développement local

Django doit écouter sur `127.0.0.1:8000` par défaut.

Dans un premier terminal, depuis la racine du dépôt :

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py runserver 127.0.0.1:8000
```

Dans un second terminal :

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Ouvrir `http://localhost:3000`.

Les appels navigateur vers `/api/*` sont proxyfiés par Next.js vers Django.

Pour utiliser une autre origine backend, copier `.env.example` vers un fichier local `.env.local` et adapter :

```text
BKO_API_ORIGIN=http://127.0.0.1:8000
```

Ne jamais y placer de secret destiné au navigateur.

## Vérification

```powershell
npm.cmd run lint
npm.cmd run build
```

Voir `../docs/etape-20-espace-client.md` pour le parcours client et les règles hors connexion.
