"use client";

import Image from "next/image";
import { useEffect, useState } from "react";

import { useBkoAlert } from "@/components/bko-alert";
import {
  apiGet,
  apiMutation,
  formatDate,
  formatXof,
  PAYMENT_STATUS_LABELS,
  type ApiPage,
  type PaymentTransaction,
  type ProviderSubscription,
  type SubscriptionPlan,
} from "@/lib/provider-api";

function paymentTone(status: PaymentTransaction["status"]) {
  if (status === "SUCCEEDED") return "success";
  if (status === "FAILED" || status === "CANCELLED") return "danger";
  return "warning";
}

type PaymentMethodProvider = "PAYDUNYA" | "WAVE";

type PaymentMethod = {
  provider: PaymentMethodProvider;
  label: string;
  available: boolean;
};

type PaymentMethods = {
  checkout?: PaymentMethod;
  methods?: PaymentMethod[];
  paydunya?: boolean;
  wave: boolean;
};

type PlanChangeKind = "new" | "renew" | "upgrade" | "downgrade";

function planChangeKind(
  subscription: ProviderSubscription | null,
  plan: SubscriptionPlan,
): PlanChangeKind {
  if (!subscription || subscription.status !== "ACTIVE") return "new";
  if (subscription.plan.id === plan.id) return "renew";
  if (
    subscription.plan.price_xof === 0
    || plan.price_xof > subscription.plan.price_xof
  ) {
    return "upgrade";
  }
  return "downgrade";
}

function hasFutureScheduledChange(subscription: ProviderSubscription | null) {
  return Boolean(
    subscription?.pending_plan
    && subscription.pending_starts_at
    && new Date(subscription.pending_starts_at).getTime() > Date.now(),
  );
}

function directPaymentMethods(payload: PaymentMethods): PaymentMethod[] {
  const fromApi = (payload.methods ?? []).filter(
    (method) =>
      method.provider === "PAYDUNYA"
      || method.provider === "WAVE",
  );
  if (fromApi.length > 0) return fromApi;

  return [
    {
      provider: "PAYDUNYA",
      label: "PayDunya (Orange Money Mali)",
      available: Boolean(payload.paydunya),
    },
    {
      provider: "WAVE",
      label: "Wave",
      available: Boolean(payload.wave),
    },
  ];
}

function methodStatusLabel(method: PaymentMethod | undefined) {
  if (!method) return "Bientôt disponible";
  return method.available ? "Disponible" : "Bientôt disponible";
}

function planPresentation(plan: SubscriptionPlan) {
  const name = plan.name.trim().toLowerCase();

  if (plan.price_xof === 0) {
    return {
      badge: "Découverte",
      subtitle: "Testez BKO Services gratuitement avant de choisir votre formule.",
      tone: "trial",
    };
  }
  if (name === "essentiel") {
    return {
      badge: "Démarrage",
      subtitle: "Une formule simple pour recevoir vos demandes normales et développer votre activité.",
      tone: "essential",
    };
  }
  if (name === "plus") {
    return {
      badge: "Recommandé",
      subtitle: "Pour les prestataires actifs qui veulent gérer davantage d’opportunités, y compris les urgences.",
      tone: "featured",
    };
  }
  if (name === "pro") {
    return {
      badge: "Premium",
      subtitle: "Pensé pour les professionnels très actifs et les équipes qui gèrent plusieurs interventions.",
      tone: "pro",
    };
  }
  return {
    badge: "BKO Services",
    subtitle: plan.description || "Un abonnement adapté à votre activité.",
    tone: "standard",
  };
}

function paymentButtonLabel(
  plan: SubscriptionPlan,
  changeKind: PlanChangeKind,
) {
  if (changeKind === "renew") return `Renouveler ${plan.name} avec PayDunya`;
  if (changeKind === "upgrade") return `Passer au plan ${plan.name}`;
  if (changeKind === "downgrade") return `Programmer le plan ${plan.name}`;
  return `Choisir ${plan.name} avec PayDunya`;
}

export default function ProviderSubscriptionPage() {
  const {
    success: showSuccess,
    error: showError,
    warning: showWarning,
    info: showInfo,
    confirmAction,
  } = useBkoAlert();

  const [subscription, setSubscription] = useState<ProviderSubscription | null>(null);
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [payments, setPayments] = useState<PaymentTransaction[]>([]);
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const paydunya = paymentMethods.find(
    (method) => method.provider === "PAYDUNYA",
  );
  const wave = paymentMethods.find((method) => method.provider === "WAVE");
  const anyPaymentAvailable = Boolean(
    paydunya?.available || wave?.available,
  );

  async function refreshPayments() {
    const page = await apiGet<ApiPage<PaymentTransaction>>(
      "/api/v1/payments/transactions/",
    );
    setPayments(page.results);
  }

  async function refreshSubscription() {
    const payload = await apiGet<{ subscription: ProviderSubscription | null }>(
      "/api/v1/subscriptions/me/",
    );
    setSubscription(payload.subscription);
    return payload.subscription;
  }

  async function refreshMethods() {
    const payload = await apiGet<PaymentMethods>("/api/v1/payments/methods/");
    setPaymentMethods(directPaymentMethods(payload));
  }

  useEffect(() => {
    let active = true;

    Promise.all([
      apiGet<{ subscription: ProviderSubscription | null }>(
        "/api/v1/subscriptions/me/",
      ),
      apiGet<ApiPage<SubscriptionPlan>>("/api/v1/subscriptions/plans/"),
      apiGet<ApiPage<PaymentTransaction>>("/api/v1/payments/transactions/"),
      apiGet<PaymentMethods>("/api/v1/payments/methods/"),
    ])
      .then(([subscriptionPayload, planPage, paymentPage, methodsPayload]) => {
        if (!active) return;
        setSubscription(subscriptionPayload.subscription);
        setPlans(planPage.results);
        setPayments(paymentPage.results);
        setPaymentMethods(directPaymentMethods(methodsPayload));
      })
      .catch((caught) => {
        if (!active) return;
        setError(
          caught instanceof Error
            ? caught.message
            : "Impossible de charger l’abonnement.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const returned = params.get("paiement");
    if (returned !== "retour" && returned !== "erreur") return;

    const transactionId = params.get("transaction");
    if (!transactionId || !/^[0-9a-f-]{36}$/i.test(transactionId)) return;

    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let attempts = 0;

    async function checkPayment() {
      try {
        const payment = await apiGet<PaymentTransaction>(
          `/api/v1/payments/transactions/${transactionId}/`,
        );
        if (!active) return;

        if (payment.status === "FAILED" || payment.status === "CANCELLED") {
          setMessage("Paiement non confirmé. Aucun abonnement n’a été activé par ce retour.");
          showWarning({
            title: "Paiement non confirmé",
            message: "Aucun abonnement n’a été activé. Vous pouvez réessayer depuis cette page.",
          });
          await refreshPayments();
          return;
        }

        if (payment.status === "SUCCEEDED" && payment.fulfilled_at) {
          const [updatedSubscription] = await Promise.all([
            refreshSubscription(),
            refreshPayments(),
          ]);
          if (active) {
            const scheduled = hasFutureScheduledChange(updatedSubscription);
            setMessage(
              scheduled
                ? "Paiement confirmé : votre prochain plan est programmé."
                : "Paiement confirmé : abonnement actualisé.",
            );
            showSuccess({
              title: scheduled ? "Changement programmé" : "Abonnement actualisé",
              message: scheduled
                ? "Votre plan actuel reste actif jusqu’à sa date de fin. Le nouveau plan prendra ensuite automatiquement le relais."
                : "Le serveur a confirmé le paiement et actualisé votre abonnement.",
            });
          }
          return;
        }

        setMessage(
          payment.status === "SUCCEEDED"
            ? "Paiement confirmé : activation en cours sur le serveur."
            : "Confirmation du paiement en attente. Ce retour ne valide aucun paiement.",
        );
        if (++attempts < 10) timer = setTimeout(checkPayment, 3000);
      } catch (caught) {
        if (active) {
          const detail = caught instanceof Error
            ? caught.message
            : "Vérification du paiement impossible.";
          setError(detail);
          showError({ title: "Vérification impossible", message: detail });
        }
      }
    }

    void checkPayment();
    return () => {
      active = false;
      if (timer) clearTimeout(timer);
    };
  }, [showError, showSuccess, showWarning]);

  async function activateTrial(plan: SubscriptionPlan) {
    const confirmed = await confirmAction({
      title: "Activer mon essai gratuit",
      message: `Votre essai ${plan.name} démarre immédiatement pour ${plan.duration_days} jours. Il ne peut être utilisé qu’une seule fois.`,
      confirmLabel: "Activer mon essai",
      cancelLabel: "Plus tard",
    });
    if (!confirmed) return;

    const actionKey = `trial:${plan.id}`;
    setBusyAction(actionKey);
    setError("");
    setMessage("");
    try {
      const activated = await apiMutation<ProviderSubscription>(
        "/api/v1/subscriptions/trial/activate/",
        "POST",
        {},
      );
      setSubscription(activated);
      setMessage("Essai gratuit activé. Rendez-vous disponible pour commencer à recevoir des offres.");
      showSuccess({
        title: "Essai activé",
        message: `Votre essai ${activated.plan.name} est maintenant actif. Vous pouvez passer disponible depuis votre profil prestataire.`,
      });
    } catch (caught) {
      const detail = caught instanceof Error
        ? caught.message
        : "Activation de l’essai impossible.";
      setError(detail);
      showError({ title: "Essai non activé", message: detail });
    } finally {
      setBusyAction(null);
    }
  }

  async function cancelScheduledChange() {
    if (
      !subscription?.pending_plan
      || !subscription.pending_starts_at
      || !subscription.pending_ends_at
    ) {
      return;
    }

    const confirmed = await confirmAction({
      title: "Annuler le changement programmé",
      message: `Le passage vers ${subscription.pending_plan.name} sera annulé. Votre plan ${subscription.plan.name} restera actif jusqu’au ${formatDate(subscription.ends_at)}.`,
      confirmLabel: "Annuler le changement",
      cancelLabel: "Garder le changement",
    });
    if (!confirmed) return;

    const actionKey = "cancel-pending-plan";
    setBusyAction(actionKey);
    setError("");
    setMessage("");
    try {
      const updated = await apiMutation<ProviderSubscription>(
        "/api/v1/subscriptions/me/pending-change/cancel/",
        "POST",
        {},
      );
      setSubscription(updated);
      setMessage("Le changement programmé a été annulé. Votre plan actuel est conservé.");
      showSuccess({
        title: "Changement annulé",
        message: `Votre plan ${updated.plan.name} reste actif jusqu’au ${formatDate(updated.ends_at)}. Vous pouvez maintenant choisir un autre plan.`,
      });
    } catch (caught) {
      const detail = caught instanceof Error
        ? caught.message
        : "Impossible d’annuler le changement programmé.";
      setError(detail);
      showError({ title: "Annulation impossible", message: detail });
    } finally {
      setBusyAction(null);
    }
  }

  async function startCheckout(plan: SubscriptionPlan, method: PaymentMethod) {
    if (plan.price_xof === 0) {
      const detail = "Ce plan gratuit s’active directement depuis BKO Services.";
      setError(detail);
      showInfo({ title: "Essai gratuit", message: detail });
      return;
    }

    if (!method.available) {
      showWarning({
        title: `${method.label} bientôt disponible`,
        message: "Les identifiants marchands de ce moyen de paiement ne sont pas encore activés sur BKO Services.",
      });
      return;
    }

    if (hasFutureScheduledChange(subscription)) {
      showWarning({
        title: "Changement déjà programmé",
        message: "Votre prochain plan est déjà enregistré. Attendez son démarrage avant d’effectuer un nouveau changement.",
      });
      return;
    }

    const changeKind = planChangeKind(subscription, plan);
    const currentEnd = subscription ? formatDate(subscription.ends_at) : "";
    const changeMessage =
      changeKind === "renew"
        ? `Votre plan ${plan.name} sera renouvelé pour ${plan.duration_days} jours supplémentaires après la période déjà acquise.`
        : changeKind === "upgrade"
          ? `Le plan ${plan.name} sera appliqué immédiatement après confirmation du paiement. Les ${plan.duration_days} jours payés seront ajoutés après votre période déjà acquise.`
          : changeKind === "downgrade"
            ? `Votre plan actuel reste actif jusqu’au ${currentEnd}. Le plan ${plan.name} prendra ensuite automatiquement le relais pour ${plan.duration_days} jours.`
            : `Le plan ${plan.name} sera activé pour ${plan.duration_days} jours après confirmation du paiement.`;

    const confirmed = await confirmAction({
      title:
        changeKind === "renew"
          ? `Renouveler ${plan.name}`
          : changeKind === "upgrade"
            ? `Passer au plan ${plan.name}`
            : changeKind === "downgrade"
              ? `Programmer le plan ${plan.name}`
              : `Souscrire au plan ${plan.name}`,
      message: `${changeMessage} Montant : ${formatXof(plan.price_xof)}. Paiement choisi : ${method.label}.`,
      confirmLabel: `Continuer avec ${method.label}`,
      cancelLabel: "Annuler",
    });
    if (!confirmed) return;

    const actionKey = `payment:${plan.id}:${method.provider}`;
    setBusyAction(actionKey);
    setError("");
    setMessage("");
    try {
      const key = `web-${crypto.randomUUID()}`;
      const payment = await apiMutation<PaymentTransaction>(
        "/api/v1/payments/checkout/",
        "POST",
        {
          plan_id: plan.id,
          idempotency_key: key,
          payment_method: method.provider,
        },
      );
      setPayments((current) => [
        payment,
        ...current.filter((item) => item.id !== payment.id),
      ]);
      if (!payment.checkout_url) {
        throw new Error("Lien de paiement indisponible.");
      }
      window.location.assign(payment.checkout_url);
    } catch (caught) {
      const detail = caught instanceof Error
        ? caught.message
        : "Impossible de lancer le paiement.";
      setError(detail);
      showError({ title: "Paiement indisponible", message: detail });
    } finally {
      setBusyAction(null);
    }
  }

  async function refreshStatus() {
    setError("");
    setMessage("");
    try {
      await Promise.all([
        refreshSubscription(),
        refreshPayments(),
        refreshMethods(),
      ]);
      setMessage("Statuts actualisés depuis le serveur.");
      showSuccess({
        title: "Statuts actualisés",
        message: "Les informations affichées viennent du serveur BKO Services.",
      });
    } catch (caught) {
      const detail = caught instanceof Error
        ? caught.message
        : "Actualisation impossible.";
      setError(detail);
      showError({ title: "Actualisation impossible", message: detail });
    }
  }

  const futureScheduledChange = hasFutureScheduledChange(subscription);

  return (
    <main>
      <section className="provider-page-head">
        <div>
          <p className="page-kicker">Abonnement</p>
          <h1>Choisissez le plan qui accompagne votre croissance</h1>
          <p>
            Développez votre activité avec BKO Services grâce à un abonnement
            adapté à votre rythme. Recevez les opportunités prévues par votre
            formule, gérez vos interventions sereinement et conservez votre
            compte, vos avis et votre historique lors d’un changement de plan.
          </p>
        </div>
        <button className="button-secondary" type="button" onClick={refreshStatus}>
          Actualiser les statuts
        </button>
      </section>

      {message && <div className="form-success">{message}</div>}
      {error && <div className="inline-error">{error}</div>}
      {loading && <div className="skeleton-list">Chargement…</div>}

      {!loading && (
        <>
          <section className="provider-current-subscription provider-subscription-hero">
            <div>
              <p className="page-kicker">Votre abonnement actuel</p>
              {subscription ? (
                <>
                  <h2>{subscription.plan.name}</h2>
                  <span className={`status-badge ${subscription.status === "ACTIVE" ? "success" : "danger"}`}>
                    {subscription.status === "ACTIVE" ? "Abonnement actif" : subscription.status}
                  </span>
                  <p>
                    Du {formatDate(subscription.starts_at)} au{" "}
                    {formatDate(subscription.ends_at)}.
                  </p>
                  {subscription.status === "EXPIRED" && (
                    <p>
                      {subscription.free_trial_used_at
                        ? "Votre essai est terminé. Pour recevoir de nouvelles offres, choisissez un plan mensuel et réglez l’abonnement. Votre compte et vos interventions restent accessibles."
                        : "Votre abonnement a expiré. Choisissez un plan actif ci-dessous et effectuez un nouveau paiement. Vous conservez votre compte ; la nouvelle période commence après confirmation du paiement."}
                    </p>
                  )}
                  <div className="subscription-entitlements">
                    <span>
                      {subscription.plan.can_receive_requests ? "✓" : "×"} Demandes normales
                    </span>
                    <span>
                      {subscription.plan.can_receive_urgent_requests ? "✓" : "×"} Demandes urgentes
                    </span>
                    <span>
                      {subscription.plan.max_active_jobs === null
                        ? "Interventions simultanées illimitées"
                        : `${subscription.plan.max_active_jobs} intervention${subscription.plan.max_active_jobs > 1 ? "s" : ""} en cours à la fois`}
                    </span>
                  </div>
                  {futureScheduledChange
                    && subscription.pending_plan
                    && subscription.pending_starts_at
                    && subscription.pending_ends_at && (
                      <div className="provider-payment-warning">
                        <strong>Prochain plan : {subscription.pending_plan.name}</strong>
                        <p>
                          Votre plan actuel reste actif jusqu’au {formatDate(subscription.pending_starts_at)}.
                          {" "}Le plan {subscription.pending_plan.name} prendra ensuite le relais jusqu’au {formatDate(subscription.pending_ends_at)}.
                        </p>
                        <button
                          className="button-secondary"
                          disabled={busyAction !== null}
                          type="button"
                          onClick={() => void cancelScheduledChange()}
                        >
                          {busyAction === "cancel-pending-plan"
                            ? "Annulation…"
                            : "Annuler ce changement programmé"}
                        </button>
                      </div>
                    )}
                </>
              ) : (
                <>
                  <h2>Bienvenue dans le réseau BKO Services</h2>
                  <p>
                    Votre profil est validé. Activez votre essai gratuit ou choisissez
                    un abonnement payant pour commencer à recevoir des offres.
                  </p>
                </>
              )}
            </div>
          </section>

          <section className="content-section">
            <div className="section-heading">
              <div>
                <p className="page-kicker">Choisir</p>
                <h2>Plans disponibles</h2>
              </div>
            </div>

            <div className="provider-plan-grid">
              {plans.map((plan) => {
                const isTrial = plan.price_xof === 0;
                const trialAlreadyUsed = Boolean(subscription?.free_trial_used_at);
                const trialBlockedByExistingSubscription = isTrial && subscription !== null;
                const changeKind = planChangeKind(subscription, plan);
                const trialBusyKey = `trial:${plan.id}`;
                const paydunyaBusyKey = `payment:${plan.id}:PAYDUNYA`;
                const waveBusyKey = `payment:${plan.id}:WAVE`;
                const presentation = planPresentation(plan);
                const isCurrentPlan = Boolean(
                  subscription?.status === "ACTIVE"
                  && subscription.plan.id === plan.id,
                );

                return (
                  <article
                    className={[
                      "provider-plan-card",
                      `provider-plan-${presentation.tone}`,
                      isCurrentPlan ? "is-current" : "",
                    ].filter(Boolean).join(" ")}
                    key={plan.id}
                  >
                    <div className="provider-plan-card-head">
                      <div>
                        <span className="request-meta">{plan.duration_days} jours</span>
                        <h3>{plan.name}</h3>
                      </div>
                      <span className="provider-plan-badge">
                        {isCurrentPlan ? "Plan actuel" : presentation.badge}
                      </span>
                    </div>

                    <p className="provider-plan-subtitle">{presentation.subtitle}</p>

                    <div className="provider-plan-price-row">
                      <strong className="provider-plan-price">
                        {formatXof(plan.price_xof)}
                      </strong>
                      <small>{plan.price_xof === 0 ? "Sans paiement" : "pour 30 jours"}</small>
                    </div>

                    <div className="subscription-entitlements">
                      <span>{plan.can_receive_requests ? "✓" : "×"} Demandes normales</span>
                      <span>{plan.can_receive_urgent_requests ? "✓" : "×"} Demandes urgentes</span>
                      <span>
                        {plan.max_active_jobs === null
                          ? "Interventions simultanées illimitées"
                          : `${plan.max_active_jobs} intervention${plan.max_active_jobs > 1 ? "s" : ""} en cours à la fois`}
                      </span>
                    </div>

                    {isTrial ? (
                      <button
                        className="button-primary button-wide"
                        disabled={busyAction !== null || trialBlockedByExistingSubscription}
                        type="button"
                        onClick={() => void activateTrial(plan)}
                      >
                        {busyAction === trialBusyKey
                          ? "Activation…"
                          : subscription === null
                            ? "Activer mon essai gratuit"
                            : trialAlreadyUsed
                              ? "Essai déjà utilisé"
                              : "Essai réservé au démarrage"}
                      </button>
                    ) : futureScheduledChange ? (
                      <button className="button-secondary button-wide" disabled type="button">
                        Changement déjà programmé
                      </button>
                    ) : (
                      <div style={{ display: "grid", gap: 10 }}>
                        <button
                          className="button-secondary button-wide"
                          disabled={busyAction !== null || !paydunya?.available}
                          type="button"
                          onClick={() => paydunya && void startCheckout(plan, paydunya)}
                        >
                          {busyAction === paydunyaBusyKey
                            ? "Préparation PayDunya…"
                            : paydunya?.available
                              ? paymentButtonLabel(plan, changeKind)
                              : "PayDunya — bientôt disponible"}
                        </button>
                        <p className="provider-payment-hint">
                          Paiement sécurisé via PayDunya · Orange Money Mali
                        </p>
                        <button
                          className="button-secondary button-wide"
                          disabled={busyAction !== null || !wave?.available}
                          type="button"
                          onClick={() => wave && void startCheckout(plan, wave)}
                        >
                          {busyAction === waveBusyKey
                            ? "Préparation Wave…"
                            : wave?.available
                              ? "Payer avec Wave"
                              : "Wave — bientôt disponible"}
                        </button>
                      </div>
                    )}

                    {isTrial && (
                      <p className="muted-copy">
                        {subscription === null
                          ? "Cet essai démarre immédiatement après votre activation et ne peut être utilisé qu’une seule fois."
                          : trialAlreadyUsed
                            ? "Votre essai gratuit a déjà été utilisé. Choisissez un plan payant pour poursuivre après son expiration."
                            : "L’essai gratuit est réservé au tout premier abonnement d’un nouveau prestataire."}
                      </p>
                    )}

                    {!isTrial
                      && !futureScheduledChange
                      && subscription?.status === "ACTIVE"
                      && changeKind !== "renew" && (
                        <p className="muted-copy">
                          {changeKind === "upgrade"
                            ? "Le plan supérieur s’applique dès confirmation du paiement."
                            : "Le plan inférieur commencera à la fin de votre période actuelle."}
                        </p>
                      )}
                  </article>
                );
              })}
            </div>
          </section>

          <section className="content-section provider-payment-section">
            <div className="section-heading">
              <div>
                <p className="page-kicker">Paiement</p>
                <h2>Moyens de paiement sécurisés</h2>
              </div>
            </div>

            <div className="provider-payment-options">
              <article className="provider-payment-method-card is-primary">
                <div className="provider-payment-brand">
                  <div className="provider-paydunya-logo-wrap">
                    <Image
                      alt="PayDunya"
                      className="provider-paydunya-logo"
                      height={36}
                      src="https://paydunya.com/images/logo_blue.png"
                      unoptimized
                      width={132}
                    />
                  </div>
                  <span className={`status-badge ${paydunya?.available ? "success" : "warning"}`}>
                    {methodStatusLabel(paydunya)}
                  </span>
                </div>
                <h3>Orange Money Mali avec PayDunya</h3>
                <p>
                  Réglez votre abonnement depuis un parcours de paiement sécurisé.
                  BKO Services attend toujours la confirmation serveur PayDunya avant
                  d’activer ou de modifier votre abonnement.
                </p>
                <div className="provider-payment-security">
                  <span>✓ Confirmation serveur</span>
                  <span>✓ Montant vérifié</span>
                  <span>✓ Référence contrôlée</span>
                </div>
              </article>

              <article className="provider-payment-method-card">
                <div className="provider-payment-brand">
                  <strong className="provider-wave-mark">W</strong>
                  <span className={`status-badge ${wave?.available ? "success" : "warning"}`}>
                    {methodStatusLabel(wave)}
                  </span>
                </div>
                <h3>Wave direct</h3>
                <p>
                  Le connecteur Wave est prévu séparément. Il deviendra disponible
                  ici dès que les identifiants marchands Wave seront configurés.
                </p>
              </article>
            </div>

            <div className="provider-payment-warning provider-payment-trust">
              <strong>
                {anyPaymentAvailable
                  ? "Paiement protégé par validation serveur"
                  : "Activation marchande en cours"}
              </strong>
              <p>
                Un simple retour du navigateur ne valide jamais un paiement.
                Seule une confirmation authentifiée du fournisseur peut activer
                l’abonnement.
              </p>
            </div>
          </section>

          <section className="content-section provider-payment-section">
            <div className="section-heading">
              <div>
                <p className="page-kicker">Transactions</p>
                <h2>Historique des paiements</h2>
              </div>
            </div>

            {payments.length === 0 ? (
              <div className="empty-state compact">
                <strong>Aucune transaction pour le moment</strong>
                <p>
                  Votre historique de paiements apparaîtra ici dès votre première
                  opération.
                </p>
              </div>
            ) : (
              <div className="provider-payment-list">
                {payments.map((payment) => (
                  <article className="provider-payment-card" key={payment.id}>
                    <div>
                      <span className="request-meta">
                        {payment.plan_name_snapshot}
                      </span>
                      <h3>{payment.merchant_reference}</h3>
                      <small>
                        {payment.payment_provider} · {formatDate(payment.created_at)}
                      </small>
                    </div>
                    <div className="provider-payment-amount">
                      <strong>{formatXof(payment.amount_xof)}</strong>
                      <span className={`status-badge ${paymentTone(payment.status)}`}>
                        {PAYMENT_STATUS_LABELS[payment.status]}
                      </span>
                      {payment.status === "PENDING" && payment.checkout_url && (
                        <a href={payment.checkout_url} rel="noopener noreferrer">
                          Reprendre le paiement
                        </a>
                      )}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </main>
  );
}
