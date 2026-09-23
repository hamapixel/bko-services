# Étape 4 — Authentification et vérification du téléphone

Cette branche prépare l'API de session et l'OTP. L'envoi réel de SMS sera intégré à l'étape SMS de la feuille de route. Aucun compte non vérifié ne doit recevoir les privilèges d'un prestataire vérifié ; les demandes et le matching ne sont pas encore disponibles.

## Endpoints présents

| Méthode | Route | Usage |
| --- | --- | --- |
| GET | `/api/v1/auth/csrf/` | Obtient un jeton CSRF ; réponse non mise en cache |
| POST | `/api/v1/auth/register/` | Inscrit uniquement un `CLIENT`, téléphone encore non vérifié |
| POST | `/api/v1/auth/login/` | Ouvre une session Django avec téléphone et mot de passe |
| POST | `/api/v1/auth/logout/` | Termine la session |
| GET / PATCH | `/api/v1/auth/me/` | Lit ou modifie les seuls champs du profil autorisés |
| POST | `/api/v1/auth/phone/request-code/` | Crée et transmet un OTP en développement local |
| POST | `/api/v1/auth/phone/verify/` | Vérifie un code à six chiffres et marque le numéro vérifié |

Le serveur rejette les champs inattendus à l'inscription et lors de la mise à jour du profil. Le rôle, `is_staff`, le téléphone et la date de vérification ne sont pas modifiables via ces endpoints. Les mots de passe passent les validateurs Django et ne sont jamais retournés. Les mutations utilisent des cookies de session `HttpOnly` et un jeton CSRF ; après chaque connexion, il faut récupérer **un nouveau** jeton auprès de `/api/v1/auth/csrf/` avant le prochain POST ou PATCH. Aucune clé d'authentification n'est stockée dans `localStorage`.

Les OTP expirent après cinq minutes, ne sont stockés que sous forme de hash et sont limités à cinq essais. L'envoi est limité par téléphone (cinq codes sur 24 heures, une minute minimale entre deux codes) ; un frein par IP existe aussi. Les limites de fréquence de DRF utilisent un cache local en développement et ne remplacent pas un rate limiting partagé entre serveurs ; ce point sera renforcé avant la production.

**Transport local seulement :** sur `localhost` avec `DJANGO_DEBUG=True`, le code est affiché dans le terminal du serveur Django pour les essais de développement. Il n'apparaît jamais dans la réponse API. Ne pas copier un OTP dans Git, dans les journaux d'audit ni dans une conversation. Hors environnement local, l'envoi renvoie `503` jusqu'à l'intégration d'un fournisseur SMS officiel. Le serveur ne prétend pas avoir envoyé un SMS réel dans ce cas.

## Vérification sans modifier la base PostgreSQL locale

Depuis la racine du dépôt :

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py check
& ".\.venv\Scripts\python.exe" backend\manage.py test apps.accounts --settings=config.test_settings
git status
```

Les tests utilisent une base SQLite en mémoire, créée puis détruite par Django. Ils vérifient la protection CSRF, l'inscription avec rôle imposé par le serveur, la connexion, le refus de modification du rôle, la déconnexion, le hash OTP, son usage unique et le verrouillage après cinq échecs. Les essais de concurrence sur PostgreSQL seront ajoutés avec les demandes urgentes.

Après la réussite des tests, appliquer uniquement la nouvelle migration à la base PostgreSQL locale :

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py migrate --plan
& ".\.venv\Scripts\python.exe" backend\manage.py migrate --noinput
& ".\.venv\Scripts\python.exe" backend\manage.py showmigrations accounts
```

Résultat attendu : `[X] 0001_initial` et `[X] 0002_otpcode`. Le code devra ensuite être relié à un fournisseur SMS réel et à un rate limiting partagé avant l'ouverture publique du service.
