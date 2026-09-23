# Étape 15 — SMS/OTP professionnel

Cette étape finalise le transport SMS réel de l'OTP téléphone tout en conservant le transport console sécurisé pour le développement local.

## Objectifs

Le système garde les règles OTP déjà mises en place :

- code à 6 chiffres ;
- stockage uniquement sous forme de hash ;
- validité : 5 minutes ;
- maximum 5 essais par code ;
- maximum 5 demandes par téléphone sur 24 heures ;
- minimum 60 secondes entre deux codes ;
- contrôle CSRF et session ;
- limitation DRF par utilisateur et IP.

L'étape 15 ajoute :

- une application Django `messaging` ;
- un journal d'envoi SMS ;
- une limite IP partagée en base entre plusieurs serveurs ;
- un adaptateur SMS réel Twilio ;
- l'invalidation immédiate du code si le fournisseur refuse l'envoi ;
- une configuration explicite par variables d'environnement.

## Transport local

En développement, si `SMS_PROVIDER` est vide, `DJANGO_DEBUG=True`, l'hôte est `localhost` ou `127.0.0.1` et l'adresse distante est loopback, le transport console continue à fonctionner.

Le code OTP n'est jamais renvoyé dans la réponse API.

Le transport console est refusé hors environnement local, même si `SMS_PROVIDER=console`.

## Transport Twilio

Le premier adaptateur de production utilise l'API HTTPS Twilio directement, sans SDK Python supplémentaire.

Configuration :

```text
SMS_PROVIDER=twilio
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_MESSAGING_SERVICE_SID=MG...
TWILIO_FROM_NUMBER=
SMS_HTTP_TIMEOUT_SECONDS=5
SMS_OTP_IP_LIMIT_PER_HOUR=20
```

Utiliser soit `TWILIO_MESSAGING_SERVICE_SID`, soit `TWILIO_FROM_NUMBER`. Si un Messaging Service SID est présent, il est prioritaire.

Les secrets doivent rester uniquement dans `.env`, jamais dans `.env.example`, GitHub, une capture d'écran ou une conversation.

API utilisée :

`POST https://api.twilio.com/2010-04-01/Accounts/{AccountSid}/Messages.json`

Le numéro destinataire est envoyé en E.164.

Documentation Twilio Mali :
https://www.twilio.com/en-us/guidelines/ml/sms

Documentation Messages API :
https://www.twilio.com/docs/messaging/api/message-resource

## Journal SMS

Le modèle `SmsDeliveryLog` conserve uniquement les métadonnées nécessaires :

- utilisateur concerné ;
- numéro destinataire ;
- usage : vérification téléphone ;
- fournisseur ;
- état `PENDING`, `ACCEPTED` ou `FAILED` ;
- identifiant du message fournisseur ;
- statut fournisseur ;
- code d'erreur technique court ;
- empreinte HMAC de l'IP ;
- dates.

**Le corps du SMS et le code OTP ne sont jamais stockés dans ce journal.**

`ACCEPTED` signifie que le fournisseur a accepté la requête API. Cela ne garantit pas encore la remise finale au téléphone.

## Limite IP partagée

La limitation DRF existante reste active. En complément, l'application calcule une empreinte HMAC de l'adresse IP avec `SECRET_KEY` puis compte les demandes OTP dans PostgreSQL.

Par défaut :

```text
SMS_OTP_IP_LIMIT_PER_HOUR=20
```

L'adresse IP brute n'est pas enregistrée dans le journal SMS.

## Échec fournisseur

Si Twilio refuse l'envoi ou si le réseau échoue :

1. le journal passe à `FAILED` ;
2. un code d'erreur technique court est conservé ;
3. l'OTP généré est immédiatement marqué consommé ;
4. l'API retourne `503` ;
5. le client ne peut donc pas utiliser un code dont l'envoi n'a pas été accepté.

## Vérification locale

Depuis la racine du dépôt :

```powershell
git pull --ff-only origin feature/sms-otp
git status

& ".\.venv\Scripts\python.exe" backend\manage.py check
& ".\.venv\Scripts\python.exe" backend\manage.py makemigrations --check --dry-run
& ".\.venv\Scripts\python.exe" backend\manage.py migrate --plan

& ".\.venv\Scripts\python.exe" backend\manage.py test apps.messaging --settings=config.test_settings
& ".\.venv\Scripts\python.exe" backend\manage.py test apps.accounts apps.locations apps.catalog apps.providers apps.requests apps.reviews apps.notifications apps.messaging --settings=config.test_settings
```

La migration attendue est :

```text
messaging.0001_initial
    Create model SmsDeliveryLog
```

Après validation :

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py migrate --noinput
& ".\.venv\Scripts\python.exe" backend\manage.py showmigrations messaging
git status
```

## Test SMS réel

Les tests automatisés simulent Twilio et n'envoient aucun SMS payant.

Un test réel ne doit être effectué qu'après création/configuration du compte fournisseur et ajout des vraies valeurs dans `.env`. Sur un compte Twilio d'essai, le numéro destinataire peut devoir être vérifié au préalable.

Ne partagez jamais `TWILIO_AUTH_TOKEN`.


## Validation locale du 23 septembre 2026

Validation effectuée avec succès :

- tests de l'application `messaging` : **6 tests OK** ;
- suite complète backend : **69 tests OK** ;
- **1 test PostgreSQL ignoré sous SQLite**, comme prévu ;
- migration `messaging.0001_initial` appliquée localement ;
- `showmigrations messaging` affiche `[X] 0001_initial` ;
- branche locale propre après validation.

Aucun SMS réel n'a été envoyé pendant les tests automatisés. Les tests Twilio utilisent des simulations et n'engagent aucun coût fournisseur.
