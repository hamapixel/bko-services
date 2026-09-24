# Étape 19 — PWA complète et fonctionnement hors connexion

Cette étape transforme le frontend Next.js de BKO Services en Progressive Web App installable et prépare le fonctionnement fiable avec une connexion instable.

Le principe central reste celui défini à l'étape 0 :

> une action métier n'est jamais considérée comme envoyée tant que le serveur ne l'a pas confirmée.

## 1. Installation PWA

Le frontend expose maintenant un manifest complet avec :

- nom `BKO Services` ;
- nom court ;
- description ;
- `start_url: /` ;
- portée `/` ;
- affichage `standalone` ;
- couleur de thème bleu BKO ;
- couleur de fond ;
- orientation portrait prioritaire ;
- icônes 192 × 192 et 512 × 512 ;
- icône maskable 512 × 512 ;
- PNG pour la compatibilité large ;
- SVG conservé comme format vectoriel complémentaire.

Les navigateurs Chromium compatibles peuvent proposer automatiquement le bouton **Installer BKO Services**.

Sur iPhone/iPad, l'application affiche l'instruction :

```text
Partager → Sur l’écran d’accueil
```

Le site doit être servi via HTTPS en production. `localhost` et `127.0.0.1` permettent le test local de l'installation PWA.

## 2. Service worker

Le service worker de l'étape 14 est conservé et enrichi.

Il gère désormais :

- le Web Push existant ;
- le clic sur les notifications ;
- le cache des ressources statiques ;
- une page hors ligne ;
- la suppression des anciennes versions de cache ;
- la prise de contrôle des pages après activation ;
- l'installation d'une nouvelle version via `SKIP_WAITING`.

Le service worker est servi avec :

```text
Cache-Control: no-cache, no-store, must-revalidate
Service-Worker-Allowed: /
```

afin d'éviter qu'une ancienne version de `sw.js` reste bloquée dans le cache HTTP.

## 3. Règles strictes de cache

Le service worker **ne met jamais en cache** :

- les routes `/api/` ;
- les POST ;
- les PATCH ;
- les PUT ;
- les DELETE ;
- les réponses privées d'une page de rôle.

Les requêtes métier restent donc sous le contrôle direct du serveur.

Les ressources pouvant être mises en cache sont limitées à :

- `/_next/static/` ;
- les icônes PWA ;
- le manifest ;
- la page `/offline`.

Pour une navigation normale, le service worker essaie toujours le réseau en premier.

Si le réseau est indisponible, il affiche la page hors ligne plutôt que de présenter une ancienne page privée comme si elle était à jour.

## 4. Page hors connexion

La route :

```text
/offline
```

explique clairement que :

- le réseau est indisponible ;
- les pages privées ne sont pas simulées ;
- les actions sensibles ne sont pas envoyées ;
- un brouillon local reste **non envoyé** ;
- l'utilisateur doit réessayer après reconnexion.

## 5. État réseau global

Le composant PWA global écoute les événements navigateur :

- `online` ;
- `offline`.

Lorsque le navigateur passe hors ligne, l'interface affiche :

```text
Hors ligne — aucune action sensible ne sera déclarée envoyée.
```

Le retour du réseau retire automatiquement cet avertissement.

## 6. Brouillons de demandes

Le fichier :

```text
frontend/lib/offline-drafts.ts
```

prépare les formulaires client des prochaines étapes.

Une demande locale utilise exactement les champs acceptés par le backend :

- `trade` ;
- `neighborhood` ;
- `title` ;
- `description` ;
- `address_detail` ;
- `priority`.

Le stockage utilise IndexedDB dans :

```text
base : bko-services
store : request-drafts
```

Chaque brouillon possède obligatoirement :

```text
kind = SERVICE_REQUEST
state = LOCAL_DRAFT
```

Il n'existe volontairement aucun état local `SENT`, `CREATED` ou `SUCCESS`.

Seul le serveur peut fournir un véritable identifiant de demande et un état métier.

## 7. Aucune synchronisation silencieuse

Les brouillons IndexedDB ne contiennent aucune fonction `fetch`.

Ils ne sont donc jamais envoyés automatiquement en arrière-plan.

Après reconnexion, l'utilisateur devra explicitement lancer l'envoi depuis l'interface client qui sera développée à l'étape 20.

Une réponse HTTP réussie du backend sera nécessaire avant de supprimer le brouillon local ou de l'afficher comme envoyé.

## 8. Mutations réseau sûres

Le fichier :

```text
frontend/lib/safe-api.ts
```

fournit une base commune pour les futures actions sensibles.

Avant tout POST/PATCH/PUT/DELETE, il vérifie l'état réseau.

Hors connexion, il lève `OfflineActionError` avec un message indiquant que l'action n'a pas été envoyée.

Cette fonction :

- utilise les cookies de session avec `credentials: include` ;
- exige le token CSRF ;
- utilise `cache: no-store` ;
- n'enregistre jamais automatiquement la mutation pour un envoi futur.

## 9. Mises à jour PWA

Lorsqu'un nouveau service worker est installé alors qu'une ancienne version contrôle déjà la page, l'interface affiche :

```text
Mettre à jour
```

L'utilisateur déclenche alors `SKIP_WAITING`.

Après le changement de contrôleur, la page se recharge pour utiliser les nouveaux fichiers.

Cela évite de mélanger pendant longtemps une ancienne interface et une nouvelle version du service worker.

## 10. Web Push préservé

Les fonctions push de l'étape 14 restent présentes.

Les notifications utilisent désormais l'icône PWA PNG.

Le clic sur une notification :

1. recherche une fenêtre BKO Services déjà ouverte ;
2. lui donne le focus si elle correspond à la cible ;
3. sinon ouvre la route demandée.

## 11. Fichiers principaux

```text
frontend/
├── app/
│   ├── layout.tsx
│   ├── manifest.ts
│   ├── offline/page.tsx
│   └── page.tsx
├── components/
│   └── pwa-client.tsx
├── lib/
│   ├── offline-drafts.ts
│   ├── push.ts
│   └── safe-api.ts
├── public/
│   ├── icons/
│   │   ├── icon-192.png
│   │   ├── icon-512.png
│   │   ├── maskable-512.png
│   │   ├── icon-192.svg
│   │   ├── icon-512.svg
│   │   └── maskable-512.svg
│   └── sw.js
└── next.config.ts
```

## 12. Validation locale automatique

Depuis la racine du dépôt :

```powershell
git pull --ff-only origin feature/pwa-offline
git status

cd frontend
npm.cmd ci
npm.cmd run lint
npm.cmd run build
cd ..

& ".\.venv\Scripts\python.exe" backend\manage.py check
git status
```

Aucune migration Django n'est ajoutée à cette étape.

## 13. Test PWA réel sur PC

Après un build réussi :

```powershell
cd frontend
npm.cmd run start
```

Ouvrir :

```text
http://localhost:3000
```

Vérifier :

1. la page BKO Services s'affiche ;
2. le manifest est disponible à `/manifest.webmanifest` ;
3. `/sw.js` répond ;
4. le navigateur propose l'installation si son environnement le permet ;
5. après installation, l'application s'ouvre en mode standalone.

Dans Chrome/Edge :

```text
F12 → Application → Service Workers
```

Le service worker doit être actif.

## 14. Test hors connexion

Important : ouvrir au moins une fois le site **en ligne** pour que le service worker s'installe et précharge `/offline`.

Ensuite :

1. ouvrir les DevTools ;
2. passer le réseau en **Offline** ;
3. recharger la page ;
4. vérifier que la page hors connexion BKO Services apparaît ;
5. vérifier l'avertissement indiquant que les actions sensibles ne sont pas envoyées ;
6. réactiver le réseau ;
7. cliquer sur **Réessayer**.

Aucune requête métier ne doit être servie depuis le cache.

## 15. Test Android

Avec une URL HTTPS accessible au téléphone :

1. ouvrir BKO Services dans Chrome ;
2. utiliser le bouton d'installation proposé par l'application ou Chrome ;
3. ouvrir l'application depuis l'écran d'accueil ;
4. vérifier le mode standalone ;
5. couper temporairement les données/Wi-Fi ;
6. vérifier l'état hors connexion ;
7. remettre Internet et vérifier le retour à l'état en ligne.

## 16. Test iPhone

Avec une URL HTTPS accessible à l'iPhone :

1. ouvrir BKO Services dans Safari ;
2. toucher **Partager** ;
3. choisir **Sur l’écran d’accueil** ;
4. confirmer l'ajout ;
5. ouvrir BKO Services depuis l'icône ;
6. vérifier l'affichage standalone ;
7. tester la perte puis le retour du réseau.

Le bouton d'installation automatique `beforeinstallprompt` n'est pas utilisé sur iPhone ; l'instruction Safari est donc affichée explicitement.

## 17. Limite volontaire de l'étape 19

Les espaces fonctionnels complets ne sont pas encore présents dans le frontend.

Les étapes suivantes utiliseront cette infrastructure :

- étape 20 : espace client ;
- étape 21 : espace prestataire ;
- étape 22 : espace administration.

L'étape 20 branchera notamment le vrai formulaire de demande sur `offline-drafts.ts` et `safe-api.ts`.

La règle restera : **un brouillon local n'est jamais une demande serveur**.


## Validation locale du 24 septembre 2026

Validation effectuée avec succès :

- `npm.cmd run lint` : **OK** ;
- `npm.cmd run build` : **OK** avec Next.js 16.3.6 / Turbopack ;
- build TypeScript : **OK** ;
- routes statiques générées : `/`, `/manifest.webmanifest`, `/offline` ;
- `manage.py check` : aucun problème ;
- suite complète backend : **104 tests OK** ;
- **1 test PostgreSQL ignoré sous SQLite**, comme prévu.

La validation réelle d'installation sur Android/iPhone et la simulation réseau hors ligne restent des vérifications manuelles de navigateur/appareil à effectuer avant production, mais le socle PWA compile et les tests de non-régression backend passent.
