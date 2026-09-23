# Étape 4 — Authentification (travail en cours)

Cette branche prépare l'API de session. La vérification du téléphone par OTP reste à ajouter **avant la clôture de l'étape 4**. Aucun compte non vérifié ne doit recevoir les privilèges d'un prestataire vérifié ; les demandes et le matching ne sont pas encore disponibles.

## Endpoints présents

| Méthode | Route | Usage |
| --- | --- | --- |
| GET | `/api/v1/auth/csrf/` | Obtient un jeton CSRF ; réponse non mise en cache |
| POST | `/api/v1/auth/register/` | Inscrit uniquement un `CLIENT`, téléphone encore non vérifié |
| POST | `/api/v1/auth/login/` | Ouvre une session Django avec téléphone et mot de passe |
| POST | `/api/v1/auth/logout/` | Termine la session |
| GET / PATCH | `/api/v1/auth/me/` | Lit ou modifie les seuls champs du profil autorisés |

Le serveur rejette les champs inattendus à l'inscription et lors de la mise à jour du profil. Le rôle, `is_staff`, le téléphone et la date de vérification ne sont pas modifiables via ces endpoints. Les mots de passe passent les validateurs Django et ne sont jamais retournés. Les mutations utilisent des cookies de session `HttpOnly` et un jeton CSRF ; après chaque connexion, il faut récupérer **un nouveau** jeton auprès de `/api/v1/auth/csrf/` avant le prochain POST ou PATCH. Aucune clé d'authentification n'est stockée dans `localStorage`.

Les limites de fréquence de DRF sont utiles en développement, mais son cache local ne remplace pas un rate limiting partagé entre serveurs ; il sera renforcé avant une mise en production. L'inscription ne constitue pas une preuve de propriété du numéro tant que l'OTP n'est pas intégré.

## Vérification sans modifier la base PostgreSQL locale

Depuis la racine du dépôt :

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py check
& ".\.venv\Scripts\python.exe" backend\manage.py test apps.accounts --settings=config.test_settings
git status
```

Les tests utilisent une base SQLite en mémoire, créée puis détruite par Django. Ils vérifient la protection CSRF, l'inscription avec rôle imposé par le serveur, la connexion, le refus de modification du rôle et la déconnexion. Les essais de concurrence sur PostgreSQL seront ajoutés avec les demandes urgentes.
