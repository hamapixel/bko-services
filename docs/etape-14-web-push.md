# Étape 14 — Web Push

Cette étape ajoute le Web Push au centre de notifications internes de BKO Services. Le SMS reste hors périmètre et sera traité à l'étape 15.

## Architecture

Le parcours est volontairement séparé en deux niveaux :

1. l'événement métier crée d'abord une `Notification` interne dans PostgreSQL ;
2. si cette notification est nouvelle et que VAPID est configuré, l'envoi Web Push est programmé avec `transaction.on_commit()`.

Ainsi, aucune notification navigateur n'est envoyée si la transaction métier est annulée.

L'envoi externe utilise `pywebpush`. Un échec d'un fournisseur push ne remet pas en cause la demande, l'attribution ou la transition métier.

## Abonnements navigateur

Le modèle `PushSubscription` conserve pour chaque navigateur :

- l'utilisateur propriétaire ;
- l'endpoint push ;
- les clés `p256dh` et `auth` nécessaires au chiffrement ;
- l'état actif/inactif ;
- le nombre d'échecs ;
- la date du dernier succès.

Un endpoint est unique globalement. Si le même navigateur change de compte, l'abonnement est réattribué au compte actuellement authentifié afin d'éviter que les notifications de deux comptes partent vers le même endpoint.

Les clés de chiffrement ne sont jamais renvoyées par l'API et ne sont pas affichées dans les formulaires Django Admin.

## API

| Méthode | Route | Accès |
| --- | --- | --- |
| GET | `/api/v1/notifications/push/config/` | Public : état + clé VAPID publique uniquement |
| POST | `/api/v1/notifications/push/subscriptions/` | Utilisateur authentifié |
| DELETE | `/api/v1/notifications/push/subscriptions/` | Utilisateur propriétaire de l'endpoint |

Exemple d'inscription :

```json
{
  "endpoint": "https://push.example/...",
  "keys": {
    "p256dh": "...",
    "auth": "..."
  }
}
```

Le client ne peut jamais transmettre un `user_id`.

## Frontend

Deux briques sont ajoutées :

- `frontend/public/sw.js` : service worker minimal qui reçoit l'événement `push`, affiche la notification et gère le clic ;
- `frontend/lib/push.ts` : fonctions réutilisables `enableWebPush()`, `disableWebPush()` et `webPushSupported()`.

La permission navigateur doit être demandée à la suite d'une action explicite de l'utilisateur, par exemple un bouton « Activer les notifications ».

Le Web Push nécessite un contexte sécurisé HTTPS en production. `localhost` reste autorisé par les navigateurs pour le développement.

## Configuration VAPID

Installer d'abord les dépendances backend mises à jour :

```powershell
& ".\.venv\Scripts\python.exe" -m pip install -r backend\requirements.txt
```

Générer ensuite une paire VAPID locale :

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py generate_vapid_keys
```

La commande affiche trois lignes :

```text
WEB_PUSH_VAPID_PUBLIC_KEY=...
WEB_PUSH_VAPID_PRIVATE_KEY=...
WEB_PUSH_VAPID_SUBJECT=mailto:votre-email@example.com
```

Copier ces valeurs dans le fichier `.env` local et remplacer l'adresse d'exemple par une adresse de contact valide.

**Ne jamais** publier la clé privée ni le fichier `.env`.

## Abonnements expirés

Si le fournisseur push répond `404` ou `410`, l'abonnement est automatiquement marqué inactif. Les autres erreurs incrémentent un compteur sans casser l'événement métier.

## Vérification locale

Depuis la racine du dépôt :

```powershell
git pull --ff-only origin feature/web-push
git status

& ".\.venv\Scripts\python.exe" -m pip install -r backend\requirements.txt

& ".\.venv\Scripts\python.exe" backend\manage.py check
& ".\.venv\Scripts\python.exe" backend\manage.py makemigrations --check --dry-run
& ".\.venv\Scripts\python.exe" backend\manage.py migrate --plan

& ".\.venv\Scripts\python.exe" backend\manage.py test apps.notifications --settings=config.test_settings
& ".\.venv\Scripts\python.exe" backend\manage.py test apps.accounts apps.locations apps.catalog apps.providers apps.requests apps.reviews apps.notifications --settings=config.test_settings

Set-Location frontend
npm run build
Set-Location ..
```

La migration attendue est `notifications.0002_pushsubscription`.

Après validation :

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py migrate --noinput
& ".\.venv\Scripts\python.exe" backend\manage.py showmigrations notifications
git status
```


## Validation locale du 23 septembre 2026

Validation effectuée avec succès :

- suite complète backend : **63 tests OK** ;
- **1 test PostgreSQL ignoré sous SQLite**, comme prévu ;
- build Next.js 16.3.6 : **OK** ;
- compilation TypeScript : **OK** ;
- génération des pages statiques : **OK** ;
- migration `notifications.0002_pushsubscription` appliquée localement ;
- `showmigrations notifications` affiche `[X] 0001_initial` et `[X] 0002_pushsubscription` ;
- branche locale propre après validation.

Les vraies clés VAPID doivent rester uniquement dans le fichier `.env` local, qui est ignoré par Git. Si une clé privée VAPID est exposée hors de cet environnement privé, la paire doit être régénérée avant utilisation.
