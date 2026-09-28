# Feuille de route vers la production

État au 28 septembre 2026. Cette page décrit le dépôt actuel, pas un environnement déjà déployé. La branche `fix/regions-auto-matching` est publiée dans une PR ; le déploiement public doit utiliser une version relue et intégrée à la branche de livraison.

## Ce qui fonctionne déjà

L'application comprend les parcours client, prestataire et administration, les lieux et métiers, les demandes et offres privées, le suivi, les avis, les plaintes, les abonnements et l'essai unique. Le backend possède une intégration Wave Checkout avec activation par webhook signé et idempotent. La PWA, les brouillons locaux et le Web Push sont présents. L'adaptateur SMS Twilio existe.

La recherche instantanée sur les métiers, les notifications internes et le compteur admin des demandes sans offre, la relance du matching lors des événements prestataire et les 19 régions administrables sont détaillés dans [couverture-mali-et-recherche.md](couverture-mali-et-recherche.md). Les subdivisions des nouvelles régions restent à renseigner avant leur ouverture aux utilisateurs.

Ces fonctionnalités ne prouvent pas encore qu'un paiement, un SMS ou une notification fonctionne avec un compte marchand réel en production. Orange Money n'est pas intégré. Le README historique mentionne Celery et Redis comme architecture cible : aucun worker Celery, Redis ou configuration Docker n'est actuellement présent dans le dépôt. La CI sur PostgreSQL et le build frontend ont réussi sur la PR ; une règle active pour `main` exige les deux contrôles.

L'obtention des comptes marchands Wave Business et Orange Money Web Payment au Mali peut démarrer maintenant, en parallèle des étapes 23–24. Si les deux moyens de paiement sont requis au lancement, l'adaptateur Orange et les essais marchands des deux parcours doivent être terminés **avant** l'étape 25 de préparation serveur. Procédure et critères : [paiements-marchands.md](paiements-marchands.md).

## Étapes restantes et critères de passage

| Étape | Travail | Preuve attendue |
| --- | --- | --- |
| 23 — Qualité | Suite PostgreSQL de base validée ; tests ajoutés pour le matching automatique et les régions. Contrôles mobiles et accessibilité à terminer. | Résultats des essais mobiles consignés ; relancer la suite complète sur PostgreSQL après cette mise à jour. |
| 24 — Automatisation | CI sur PostgreSQL et frontend validée sur la PR ; règle `main` active et deux contrôles requis. | Les deux jobs passent sur la PR et sont requis pour mettre à jour `main`. |
| 25 — Préparation serveur | Paramètres Django de production, serveur WSGI, fichiers statiques, reverse proxy HTTPS, stockage durable des avatars, sauvegardes et journaux ; décider si Redis/worker est nécessaire aux notifications et aux limites de débit entre processus. | `check --deploy` examiné, services relancés automatiquement, sauvegarde et restauration testées. |
| 26 — Préproduction | Domaine de test HTTPS, vraie livraison SMS, Web Push, installation iPhone/Android, essais et abonnements, paiement Wave sous contrat marchand. | Tests sur appareils réels, webhook signé, expiration et renouvellement constatés ; incident simulé. |
| 27 — Ouverture | Relecture de la PR, intégration, sauvegarde, migration, déploiement contrôlé, surveillance et support. | Parcours de bout en bout réussi sur le domaine final et plan de retour arrière documenté. |

Pour l'étape 23, les commandes PostgreSQL sur Windows et les contrôles manuels mobiles figurent dans [etape-23-qualite.md](etape-23-qualite.md). Le 26 septembre, la suite complète a réussi sur PostgreSQL 18.4 : **130 tests OK, aucun ignoré**. Il reste à consigner les essais mobiles et d'accessibilité. Le workflow PostgreSQL de l'étape 24 et la configuration des contrôles requis sont décrits dans [etape-24-ci.md](etape-24-ci.md).

Le contrôle local `manage.py check --deploy` signale actuellement l'absence de HSTS et de redirection HTTPS au niveau Django (ceux-ci peuvent être assurés par le reverse proxy si configurés et vérifiés), plus la clé volontairement faible utilisée pour l'audit. `STATIC_ROOT` et un serveur WSGI de production restent à configurer. Après la présente modification, la suite SQLite passe **134 tests, dont 2 ignorés** (réservés à PostgreSQL). L'ancien résultat PostgreSQL de 130 tests doit être renouvelé sur la nouvelle version. Ces résultats locaux ne remplacent pas l'exécution GitHub Actions sur la PR.

## Schéma de déploiement conseillé pour la première version

Un **seul domaine HTTPS** simplifie les cookies de session et la protection CSRF. Sur un serveur Linux disposant de stockage persistant :

```text
Navigateur / PWA → Caddy (HTTPS)
  /api/*, /django-admin/*, /health/ → Django/Gunicorn (127.0.0.1:8000)
  /static/* → fichiers Django collectés (lecture seule)
  autres chemins → Next.js `next start` (127.0.0.1:3000)
                                Django → PostgreSQL privé
```

Ne rendre publics que les ports 80 et 443. Isoler PostgreSQL et les serveurs applicatifs du réseau public. Si Caddy transmet `X-Forwarded-Proto`, Django peut utiliser `SECURE_PROXY_SSL_HEADER` **uniquement** lorsque le proxy est de confiance et que le backend n'est pas accessible directement. Les avatars sont servis par l'API authentifiée : conserver leur répertoire sur un volume durable privé et le sauvegarder avec la base. Les fichiers `.env` et les clés ne sont pas versionnés.

Le dépôt n'inclut pas encore de configuration serveur prête à exécuter. Exemple de routage à adapter **après** l'étape 25 (le chemin `STATIC_ROOT` doit d'abord être ajouté dans Django) :

```caddyfile
services.example.com {
    handle_path /static/* {
        root * /srv/bko-services/backend/staticfiles
        file_server
    }
    handle /api/* {
        reverse_proxy 127.0.0.1:8000
    }
    handle /django-admin/* {
        reverse_proxy 127.0.0.1:8000
    }
    handle /health/ {
        reverse_proxy 127.0.0.1:8000
    }
    handle {
        reverse_proxy 127.0.0.1:3000
    }
}
```

Caddy obtient un certificat HTTPS pour un domaine pointant vers le serveur si les ports 80/443 sont accessibles. Next.js doit être construit avec `npm ci && npm run build` puis lancé avec `npm run start` ; le serveur Django de développement (`runserver`) ne convient pas à la production. Installer un serveur WSGI tel que Gunicorn dans les dépendances de production, puis lancer `config.wsgi:application` sous un gestionnaire de services. Configurer `STATIC_ROOT`, exécuter `collectstatic` et servir ce répertoire séparément. Ces ajouts de code et de configuration font partie de l'étape 25 : ne pas copier cet exemple Caddy sur un serveur public avant qu'ils existent.

Variables minimales à renseigner côté serveur, avec des valeurs propres au domaine : `DJANGO_SECRET_KEY` aléatoire et durable, `DJANGO_DEBUG=False`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS=https://...`, les identifiants PostgreSQL, et `BKO_API_ORIGIN=http://127.0.0.1:8000` pour Next.js. Sur un seul domaine, Caddy envoie normalement `/api/*` directement à Django ; les réécritures Next restent utiles hors du proxy. Ne pas employer les valeurs de `.env.example` comme secrets de production.

Configurer ensuite le transport SMS, les clés VAPID, et, **après obtention du compte Wave Business Checkout**, `PAYMENT_PROVIDER=WAVE`, `WAVE_API_KEY`, `WAVE_WEBHOOK_SECRET`, `PAYMENT_RETURN_ORIGIN=https://services.example.com`. L'URL du webhook à enregistrer chez Wave est `https://services.example.com/api/v1/payments/webhooks/wave/`. La page de retour dans le navigateur n'active jamais un abonnement. Le paiement Orange Money attend les identifiants marchands et une intégration signée distincte.

## Ordre d'une mise en ligne, lorsque les prérequis sont satisfaits

1. Choisir le domaine et l'hébergement, préparer DNS, serveur, PostgreSQL et un stockage durable. Préparer une préproduction séparée.
2. Intégrer la PR relue, faire passer la CI PostgreSQL et construire les applications sur la version de livraison.
3. Installer les secrets hors du dépôt, le proxy HTTPS, le service Next.js et le service Django. Configurer les cookies sécurisés, CSRF, les fichiers statiques et les en-têtes proxy ; vérifier `manage.py check --deploy`.
4. Sauvegarder base et avatars. Appliquer `manage.py migrate --noinput` puis `manage.py collectstatic --noinput`, démarrer les services et vérifier `/health/`, la connexion et la console admin.
5. Tester le parcours complet, les permissions, le SMS, les notifications et, avec les accès marchands réels, le paiement et son webhook. Vérifier la restauration d'une sauvegarde sur une autre instance.
6. Activer la surveillance (erreurs serveur, espace disque, sauvegardes, livraisons SMS, paiements reçus mais non appliqués) et documenter les procédures de reprise. Garder un instantané des fichiers et de la base avant chaque livraison.

Une expiration d'abonnement coupe les **nouvelles offres**, sans supprimer le compte ni les interventions déjà attribuées. Le passage essai → plan payant et le renouvellement après expiration doivent faire partie des tests de préproduction.

## Documentation technique officielle

- Django : https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/ et https://docs.djangoproject.com/en/5.2/howto/static-files/deployment/
- Django avec Gunicorn : https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/gunicorn/
- Next.js auto-hébergé : https://nextjs.org/docs/app/guides/self-hosting
- Caddy HTTPS et reverse proxy : https://caddyserver.com/docs/quick-starts/reverse-proxy
- PostgreSQL `pg_dump` et `pg_restore` : https://www.postgresql.org/docs/current/app-pgdump.html et https://www.postgresql.org/docs/current/app-pgrestore.html
- Wave Checkout et webhook : https://docs.wave.com/checkout et https://docs.wave.com/webhook
