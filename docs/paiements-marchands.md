# Paiements d'abonnement : Wave et Orange Money au Mali

État au 26 septembre 2026. Aucun identifiant marchand n'est conservé dans Git ou dans le navigateur. Un retour vers l'application après paiement n'active jamais un abonnement.

## Obtenir les accès

### Wave Business

1. Faire ouvrir ou activer un **compte Wave Business** au nom de l'entité qui encaissera les abonnements BKO Services. Confirmer avec Wave que Checkout API est activé pour ce portefeuille au Mali et demander les conditions commerciales et les modalités de test.
2. Un administrateur du portefeuille ouvre la section **Developer** du portail Wave Business, puis crée une clé API avec les seuls droits nécessaires à Checkout. Si cette section n'apparaît pas, demander son activation au support API Wave. Copier la clé une fois et la conserver uniquement sur le serveur.
3. Enregistrer dans le portail Wave un webhook HTTPS pour l'événement `checkout.session.completed`. Choisir le **Signing Secret** (signature HMAC) et conserver ce secret séparément de la clé API. L'URL prévue par le projet est `https://VOTRE-DOMAINE/api/v1/payments/webhooks/wave/`.
4. Après attribution d'un domaine HTTPS, configurer sur le serveur `WAVE_API_KEY`, `WAVE_WEBHOOK_SECRET`, `PAYMENT_RETURN_ORIGIN=https://VOTRE-DOMAINE` et `PAYMENT_PROVIDER=WAVE`. Ne jamais saisir ces secrets dans le frontend, dans GitHub ou dans une conversation.

Le dépôt possède déjà `POST /api/v1/payments/wave/checkout/`, le retour en lecture seule et le webhook Wave signé. Le plan et le montant sont figés côté serveur ; la confirmation vérifie la référence, la session, le montant et XOF avant d'activer le plan. Cette implémentation doit encore être éprouvée avec un **vrai compte marchand** et un domaine HTTPS. Le navigateur ouvre `wave_launch_url` ; la page de retour ne confirme pas le paiement.

### Orange Money Web Payment / M Payment

1. S'inscrire sur **Orange Developer**, créer l'application BKO Services et demander l'API **Orange Money Web Payment / M Payment pour le Mali**. Le formulaire « Apply for Orange Money » transmet la demande à l'équipe locale après connexion.
2. S'adresser également à **Orange Mali** pour le statut marchand Orange Money, les pièces d'enregistrement/KYA demandées, le contrat, les frais, les plafonds et la procédure de test. Un simple compte Orange Money personnel ou une clé OAuth d'une autre API Orange ne suffit pas à ouvrir l'encaissement Web Payment.
3. Demander le **dossier technique propre au contrat Mali** : environnements de test et de production, identifiants marchands, création du paiement, suivi serveur du statut, authentification des notifications, retour navigateur, expiration, remboursements et règles de renouvellement. Obtenir des transactions de test et la procédure de passage en production.
4. Ne développer l'adaptateur Orange qu'à partir de cette documentation et de l'accès de test attribués par Orange. Ne pas reprendre des endpoints ou signatures d'un autre pays, ni traiter un simple retour navigateur comme preuve de paiement.

**Texte court pour les demandes marchandes (à adapter à l'entité qui encaisse)** : « BKO Services est une plateforme de mise en relation de clients et de prestataires au Mali. Les prestataires choisissent un abonnement de 30 jours à 2 000, 4 000 ou 5 000 FCFA ; un essai gratuit de 14 jours est activé par l'administration. Nous souhaitons encaisser ces abonnements en ligne en XOF via votre API Checkout/Web Payment, avec confirmation serveur sécurisée, gestion des échecs et réabonnements. Merci de nous indiquer les pièces requises, frais, accès de test, documentation technique Mali et conditions de mise en production. »

L'API Orange Web Payment est annoncée comme disponible au Mali, mais **le dépôt ne contient pas encore d'adaptateur Orange**. `GET /api/v1/payments/methods/` signale `orange_money: false` et aucun bouton de paiement Orange actif n'est affiché. Le webhook générique de test est refusé lorsque `PAYMENT_PROVIDER=ORANGE_MONEY` : il ne constitue pas une intégration Orange.

## Travail d'intégration Orange dès réception du contrat

1. Ajouter un adaptateur serveur séparé de Wave pour demander le paiement selon la spécification Orange et sauvegarder l'identifiant distant et la référence interne dans `PaymentTransaction`. Prévoir une migration si les tailles/champs actuels ne conviennent pas aux identifiants réels.
2. Ajouter un endpoint de démarrage authentifié et protégé contre les doubles clics. Le plan actif, le montant XOF et le prestataire viennent du backend, jamais d'un montant soumis par le navigateur.
3. Créer la confirmation serveur selon **la méthode officiellement fournie par Orange**. Vérifier l'authenticité de la notification et/ou consulter le statut directement auprès d'Orange ; comparer référence, marchand, montant, devise et état final. N'appeler `process_verified_webhook` qu'après cette vérification, avec `expected_provider="ORANGE_MONEY"`. Garder les événements idempotents et les états terminaux immuables.
4. Afficher le bouton Orange seulement si la configuration et l'accès marchand sont réellement opérationnels. Le retour navigateur affiche « en attente », « échoué » ou « confirmé par le serveur », sans activation.
5. Tester le parcours inscription → vérification → choix du plan → paiement → webhook/statut → abonnement → offres, puis l'expiration et le réabonnement. Tester aussi annulation, paiement dupliqué, montant erroné, notification falsifiée, notification retardée et absence de callback.

## Critères avant la mise en ligne des paiements

- Comptes marchands et contrats validés pour **les deux moyens** si les deux doivent être proposés au lancement ; conditions tarifaires connues et documentées.
- Domaine HTTPS et secrets stockés côté serveur ; les endpoints de retour n'accordent aucun droit.
- Transactions réelles ou scénarios officiels de test rapprochés avec les reçus marchands, journaux et lignes de la plateforme. Un paiement confirmé sans abonnement déclenche une alerte et un retraitement contrôlé.
- Les scénarios de refus, d'expiration, de renouvellement et de webhook rejoué sont passés sur PostgreSQL en préproduction.
- L'ancien fournisseur `GENERIC`/`TEST` reste réservé aux tests et ne doit pas être configuré comme moyen d'encaissement public.

## Sources officielles

- Wave Business APIs et gestion des clés : https://docs.wave.com/business
- Wave Checkout : https://docs.wave.com/checkout
- Wave Webhooks : https://docs.wave.com/webhook
- Orange Money Web Payment : https://developer.orange.com/apis/om-webpay
- Demande d'accès Orange : https://developer.orange.com/products/payment/apply-orange-money/
- Orange Developer Mali : https://www.orangemali.com/fr/orange-developer.html
