# Étape 18 — Paiements sécurisés et activation d'abonnement

Cette étape ajoute le noyau de paiement serveur de BKO Services. Le flux est volontairement indépendant d'un fournisseur particulier afin de pouvoir brancher ensuite Orange Money, Moov Money, un agrégateur ou un autre prestataire sans modifier les règles métier.

## Wave et Orange Money (septembre 2026)

Le paiement Wave utilise maintenant l'API officielle Checkout : `POST /api/v1/payments/wave/checkout/` crée une session pour le prix du plan côté serveur, puis retourne le lien `pay.wave.com` au prestataire. L'URL de retour dans le navigateur ne valide jamais l'abonnement. Seul `POST /api/v1/payments/webhooks/wave/`, après vérification de `Wave-Signature` (corps brut + horodatage de moins de cinq minutes), de la session Wave, du montant XOF et de la référence unique, active ou renouvelle l'abonnement. Une même confirmation reçue plusieurs fois ne prolonge pas deux fois la durée. Le webhook générique ne peut pas confirmer une transaction Wave.

Le bouton Wave reste désactivé sans configuration marchande. Pour le rendre disponible, il faut :

1. un compte **Wave Business** autorisé à utiliser Checkout et une clé API limitée aux besoins de Checkout ;
2. une URL HTTPS publique pour le site et l'API ;
3. enregistrer `https://<domaine-api>/api/v1/payments/webhooks/wave/` dans le portail Wave pour l'événement `checkout.session.completed` et obtenir le secret de signature ;
4. configurer côté **backend uniquement** `PAYMENT_PROVIDER=WAVE`, `WAVE_API_KEY`, `WAVE_WEBHOOK_SECRET` et `PAYMENT_RETURN_ORIGIN=https://<domaine-site>` (sans chemin), laisser `PAYMENT_WEBHOOK_SECRET` vide, puis appliquer la migration `payments.0002` et redémarrer les serveurs ;
5. effectuer un essai réel de faible montant sur un environnement de test du marchand et vérifier paiement, notification et renouvellement avant l'ouverture publique.

Il faut également un compte marchand Orange Money Web Payment au Mali et un accès API approuvé par Orange (ou un partenaire sous contrat). Le bouton Orange Money reste indisponible en attendant ces accès et l'intégration des callbacks propres à Orange. Aucun transfert vers un numéro personnel, capture de paiement ou retour navigateur ne peut activer automatiquement un abonnement. Les commissions et conditions sont celles du contrat marchand.

Documentation officielle : https://docs.wave.com/checkout , https://docs.wave.com/webhook , https://developer.orange.com/apis/om-webpay .

## Principe de sécurité

Le frontend ne peut jamais déclarer un paiement réussi.

Le parcours est :

1. le prestataire choisit un plan ;
2. le serveur crée une transaction `PENDING` avec le prix et la durée figés ;
3. une référence marchande unique `BKO-...` est générée ;
4. le fournisseur de paiement utilise cette référence ;
5. le fournisseur appelle le webhook serveur ;
6. le serveur vérifie la signature HMAC ;
7. le montant, la devise et la référence fournisseur sont contrôlés ;
8. seulement après un statut `SUCCESS` valide, l'abonnement est activé ou renouvelé.

Aucun paramètre envoyé par le navigateur ne peut directement activer un abonnement.

## Transaction de paiement

`PaymentTransaction` conserve notamment :

- le prestataire ;
- le plan choisi ;
- le but initial : `ACTIVATE` ou `RENEW` ;
- le fournisseur configuré ;
- une référence marchande unique ;
- une référence de transaction fournisseur unique ;
- une clé d'idempotence propre au prestataire ;
- le montant en FCFA ;
- la devise `XOF` ;
- un snapshot du code, du nom et de la durée du plan ;
- le statut ;
- la date de confirmation ;
- la date d'application à l'abonnement ;
- un code d'erreur de fulfillment éventuel.

Statuts :

- `PENDING` ;
- `SUCCEEDED` ;
- `FAILED` ;
- `CANCELLED`.

Les états terminaux ne sont pas réécrits par un webhook contradictoire.

## Prix et durée figés

Le prix et la durée sont copiés dans la transaction au moment de sa création.

Si un administrateur modifie ensuite le plan, la transaction déjà initiée conserve :

- son montant d'origine ;
- sa durée d'origine.

Un webhook avec un montant différent ou une autre devise est rejeté et audité.

## Idempotence

Le client fournit une `idempotency_key` de 8 à 64 caractères autorisés.

La contrainte est unique par prestataire.

Répéter la même demande avec la même clé et le même plan retourne la transaction existante au lieu d'en créer une seconde.

Réutiliser la même clé pour un autre plan est refusé.

Le webhook est également idempotent :

- le corps brut est haché en SHA-256 ;
- un événement identique n'est enregistré qu'une fois ;
- un paiement déjà appliqué ne prolonge jamais l'abonnement une deuxième fois.

## Webhook signé

Route :

```text
POST /api/v1/payments/webhooks/provider/
```

Le webhook n'utilise pas la session utilisateur et est exempté de CSRF car il est appelé serveur à serveur.

Sa protection repose sur :

```text
X-BKO-Payment-Signature
```

La valeur attendue est un HMAC-SHA256 du corps HTTP brut avec `PAYMENT_WEBHOOK_SECRET`.

Le secret :

- n'est jamais envoyé au frontend ;
- n'est jamais stocké en base ;
- n'est jamais commité ;
- reste uniquement dans le fichier `.env` ou le gestionnaire de secrets de production.

Si aucun secret n'est configuré, le webhook répond `503` au lieu d'accepter des paiements non vérifiés.

Payload générique V1 :

```json
{
  "merchant_reference": "BKO-...",
  "provider_transaction_id": "reference-fournisseur",
  "status": "SUCCESS",
  "amount_xof": 5000,
  "currency": "XOF"
}
```

Statuts externes acceptés :

- `SUCCESS` ;
- `FAILED` ;
- `CANCELLED`.

Un adaptateur fournisseur réel devra convertir son webhook officiel vers ce contrat ou reprendre la même logique de vérification avant d'appeler le service métier.

## Audit des webhooks

`PaymentWebhookEvent` journalise les callbacks signés sans conserver le payload brut.

Sont conservés :

- l'empreinte SHA-256 ;
- la transaction ;
- le statut annoncé ;
- la référence fournisseur ;
- le montant ;
- la devise ;
- l'acceptation ou le rejet ;
- un code d'erreur sûr ;
- la date de réception.

Exemples de rejets audités :

- `amount_or_currency_mismatch` ;
- `provider_transaction_reused` ;
- `terminal_status_conflict`.

Une signature invalide n'est pas enregistrée comme événement métier validé.

## Application à l'abonnement

Un paiement `SUCCESS` appelle le service interne `apply_paid_subscription`.

Si le prestataire possède un abonnement encore actif :

- la durée payée est ajoutée à la date de fin existante ;
- l'historique reçoit `RENEWED`.

Sinon :

- une nouvelle période commence immédiatement ;
- l'historique reçoit `ACTIVATED`.

Une intervention déjà attribuée n'est pas interrompue.

## Paiement réussi mais abonnement non appliqué

Le paiement et l'abonnement sont deux réalités distinctes.

Si le fournisseur confirme que l'argent est reçu mais que le prestataire a été suspendu entre-temps :

- la transaction reste `SUCCEEDED` ;
- aucun faux échec financier n'est enregistré ;
- `fulfillment_error_code` devient `subscription_fulfillment_failed` ;
- l'administration peut corriger la situation puis relancer uniquement l'application de l'abonnement.

Route :

```text
POST /api/v1/payments/admin/transactions/<uuid>/retry-fulfillment/
```

Cette action ne peut jamais transformer un paiement non réussi en paiement réussi.

## Référence fournisseur unique

`provider_transaction_id` est unique.

Une référence fournisseur déjà utilisée par une autre transaction est rejetée afin d'empêcher qu'un même encaissement soit utilisé pour activer plusieurs abonnements.

## API prestataire

| Méthode | Route | Usage |
| --- | --- | --- |
| GET | `/api/v1/payments/transactions/` | Ses paiements uniquement |
| POST | `/api/v1/payments/transactions/` | Initier un paiement |
| GET | `/api/v1/payments/transactions/<uuid>/` | Détail de son paiement |

Les UUID étrangers retournent `404`.

La création exige :

- un compte actif ;
- le rôle `PROVIDER` ;
- un téléphone vérifié ;
- un profil prestataire `VERIFIED` ;
- un plan actif et payant.

## API d'audit administratif

L'accès exige le SUPERADMIN ou un ADMIN staff possédant `payments.manage_payments`.

| Méthode | Route | Usage |
| --- | --- | --- |
| GET | `/api/v1/payments/admin/transactions/` | Toutes les transactions |
| GET | `/api/v1/payments/admin/transactions/<uuid>/` | Détail d'audit |
| POST | `/api/v1/payments/admin/transactions/<uuid>/retry-fulfillment/` | Retenter l'abonnement d'un paiement déjà réussi |

Aucune route administrative ne permet de marquer manuellement un paiement comme `SUCCEEDED`.

## Configuration

`.env.example` contient uniquement des placeholders :

```text
PAYMENT_PROVIDER=GENERIC
PAYMENT_WEBHOOK_SECRET=
```

Le dépôt ne contient aucune vraie clé.

Le provider `GENERIC` décrit le contrat serveur. Le branchement d'un fournisseur réel nécessitera ses identifiants et sa méthode officielle de signature avant production.

## Limitation d'abus

La création de transactions utilise :

```text
payment_create = 10/hour
```

L'idempotence reste la protection principale contre les doubles clics et répétitions réseau.

## Django Admin

Les transactions et événements sont visibles en lecture seule.

Le Django Admin ne peut ni créer, ni modifier, ni supprimer directement une transaction financière.

## Validation locale

Depuis la racine du dépôt :

```powershell
git pull --ff-only origin feature/payments
git status

& ".\.venv\Scripts\python.exe" backend\manage.py check
& ".\.venv\Scripts\python.exe" backend\manage.py makemigrations --check --dry-run
& ".\.venv\Scripts\python.exe" backend\manage.py migrate --plan

& ".\.venv\Scripts\python.exe" backend\manage.py test apps.payments --settings=config.test_settings

& ".\.venv\Scripts\python.exe" backend\manage.py test apps.accounts apps.locations apps.catalog apps.providers apps.requests apps.reviews apps.notifications apps.messaging apps.complaints apps.subscriptions apps.payments --settings=config.test_settings
```

La migration attendue est :

```text
payments.0001_initial
    Create model PaymentTransaction
    Create model PaymentWebhookEvent
```

Après validation complète :

```powershell
& ".\.venv\Scripts\python.exe" backend\manage.py migrate --noinput
& ".\.venv\Scripts\python.exe" backend\manage.py showmigrations payments
git status
```


## Validation locale du 24 septembre 2026

Validation effectuée avec succès :

- tests de l'application `payments` : **14 tests OK** ;
- suite complète backend : **104 tests OK** ;
- **1 test PostgreSQL ignoré sous SQLite**, comme prévu ;
- `manage.py check` : aucun problème ;
- `makemigrations --check --dry-run` : aucune modification détectée ;
- migration `payments.0001_initial` appliquée localement ;
- `showmigrations payments` affiche `[X] 0001_initial` ;
- branche locale propre après validation.
