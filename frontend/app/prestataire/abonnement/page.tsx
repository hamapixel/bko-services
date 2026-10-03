"use client";

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

type PaymentMethods = {
  checkout?: {
    provider: string;
    label: string;
    available: boolean;
  };
  wave: boolean;
  orange_money: boolean;
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
  const [checkoutAvailable, setCheckoutAvailable] = useState(false);
  const [checkoutLabel, setCheckoutLabel] = useState("Paiement mobile");
  const [loading, setLoading] = useState(true);
  const [busyPlan, setBusyPlan] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

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
      .then(([subscriptionPayload, planPage, paymentPage, methods]) => {
        if (!active) return;
        setSubscription(subscriptionPayload.subscription);
        setPlans(planPage.results);
        setPayments(paymentPage.results);
        if (methods.checkout) {
          setCheckoutAvailable(methods.checkout.available);
          setCheckoutLabel(methods.checkout.label || "Paiement mobile");
        } else {
          setCheckoutAvailable(methods.wave);
          setCheckoutLabel(methods.wave ? "Wave" : "Paiement mobile");
        }
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
    if (!transactionId || !/^[0-9a-f-]{36}$/i.test(transactionId)) {
      return;
    }

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
          const detail = caught instanceof Error ? caught.message : "Vérification du paiement impossible.";
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

    setBusyPlan(plan.id);
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
      const detail = caught instanceof Error ? caught.message : "Activation de l’essai impossible.";
      setError(detail);
      showError({ title: "Essai non activé", message: detail });
    } finally {
      setBusyPlan(null);
    }
  }

  async function startCheckout(plan: SubscriptionPlan) {
    if (plan.price_xof === 0) {
      const detail = "Ce plan gratuit s’active directement depuis BKO Services.";
      setError(detail);
      showInfo({ title: "Essai gratuit", message: detail });
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
      message: `${changeMessage} Montant : ${formatXof(plan.price_xof)}. Vous serez redirigé vers ${checkoutLabel}.`,
      confirmLabel: "Continuer vers le paiement",
      cancelLabel: "Annuler",
    });
    if (!confirmed) return;

    setBusyPlan(plan.id);
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
      const detail =
        caught instanceof Error
          ? caught.message
          : "Impossible de lancer le paiement.";
      setError(detail);
      showError({ title: "Paiement indisponible", message: detail });
    } finally {
      setBusyPlan(null);
    }
  }

  async function refreshStatus() {
    setError("");
    setMessage("");
    try {
      await Promise.all([refreshSubscription(), refreshPayments()]);
      setMessage("Statuts actualisés depuis le serveur.");
      showSuccess({
        title: "Statuts actualisés",
        message: "Les informations affichées viennent du serveur BKO Services.",
      });
    } catch (caught) {
      const detail = caught instanceof Error ? caught.message : "Actualisation impossible.";
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
          <h1>Plans et paiements</h1>
          <p>
            Votre droit à recevoir de nouvelles offres dépend d’un abonnement
            effectif. Vous pouvez renouveler ou changer de plan sans perdre
            votre compte, vos avis ni vos interventions déjà attribuées.
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
          <section className="provider-current-subscription">
            <div>
              <p className="page-kicker">Plan actuel</p>
              {subscription ? (
                <>
                  <h2>{subscription.plan.name}</h2>
                  <span className={`status-badge ${subscription.status === "ACTIVE" ? "success" : "danger"}`}>
                    {subscription.status}
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
                    <span>{subscription.plan.max_active_jobs === null ? "Interventions simultanées illimitées" : `${subscription.plan.max_active_jobs} intervention${subscription.plan.max_active_jobs > 1 ? "s" : ""} en cours à la fois`}</span>
                  </div>
                  {futureScheduledChange && subscription.pending_plan && subscription.pending_starts_at && subscription.pending_ends_at && (
                    <div className="provider-payment-warning">
                      <strong>Prochain plan : {subscription.pending_plan.name}</strong>
                      <p>
                        Votre plan actuel reste actif jusqu’au {formatDate(subscription.pending_starts_at)}.
                        {" "}Le plan {subscription.pending_plan.name} prendra ensuite le relais jusqu’au {formatDate(subscription.pending_ends_at)}.
                      </p>
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
                const disabled =
                  busyPlan !== null
                  || (isTrial
                    ? trialBlockedByExistingSubscription
                    : futureScheduledChange || !checkoutAvailable);

                const paidLabel =
                  changeKind === "renew"
                    ? `Renouveler avec ${checkoutLabel}`
                    : changeKind === "upgrade"
                      ? `Passer à ${plan.name}`
                      : changeKind === "downgrade"
                        ? `Programmer ${plan.name}`
                        : `Payer avec ${checkoutLabel}`;

                return (
                  <article className="provider-plan-card" key={plan.id}>
                    <div>
                      <span className="request-meta">{plan.duration_days} jours</span>
                      <h3>{plan.name}</h3>
                      <p>{plan.description || "Plan BKO Services."}</p>
                    </div>
                    <strong className="provider-plan-price">
                      {formatXof(plan.price_xof)}
                    </strong>
                    <div className="subscription-entitlements">
                      <span>{plan.can_receive_requests ? "✓" : "×"} Demandes normales</span>
                      <span>{plan.can_receive_urgent_requests ? "✓" : "×"} Demandes urgentes</span>
                      <span>{plan.max_active_jobs === null ? "Interventions simultanées illimitées" : `${plan.max_active_jobs} intervention${plan.max_active_jobs > 1 ? "s" : ""} en cours à la fois`}</span>
                    </div>
                    <button
                      className="button-primary button-wide"
                      disabled={disabled}
                      type="button"
                      onClick={() => void (isTrial ? activateTrial(plan) : startCheckout(plan))}
                    >
                      {busyPlan === plan.id
                        ? isTrial ? "Activation…" : "Préparation…"
                        : isTrial
                          ? subscription === null
                            ? "Activer mon essai gratuit"
                            : trialAlreadyUsed
                              ? "Essai déjà utilisé"
                              : "Essai réservé au démarrage"
                          : futureScheduledChange
                            ? "Changement déjà programmé"
                            : checkoutAvailable
                              ? paidLabel
                              : "Paiement bientôt disponible"}
                    </button>
                    {isTrial && (
                      <p className="muted-copy">
                        {subscription === null
                          ? "Cet essai démarre immédiatement après votre activation et ne peut être utilisé qu’une seule fois."
                          : trialAlreadyUsed
                            ? "Votre essai gratuit a déjà été utilisé. Choisissez un plan payant pour poursuivre après son expiration."
                            : "L’essai gratuit est réservé au tout premier abonnement d’un nouveau prestataire."}
                      </p>
                    )}
                    {!isTrial && !futureScheduledChange && subscription?.status === "ACTIVE" && changeKind !== "renew" && (
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
                <p className="page-kicker">Transactions</p>
                <h2>Historique des paiements</h2>
              </div>
            </div>

            <div className="provider-payment-warning">
              <strong>{checkoutAvailable ? checkoutLabel : "Paiement mobile bientôt disponible"}</strong>
              <p>
                {checkoutAvailable
                  ? "Après le paiement, BKO Services attend la confirmation sécurisée du fournisseur. Seule cette confirmation serveur peut activer, renouveler ou programmer un changement de plan."
                  : "L’agrégateur de paiement n’est pas encore connecté. Aucun paiement n’est encaissé sur cette page pour le moment."}
              </p>
            </div>

            {payments.length === 0 ? (
              <div className="empty-state compact">
                <strong>Aucune transaction</strong>
                <p>Les transactions que vous préparez apparaîtront ici.</p>
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
                      <small>{formatDate(payment.created_at)}</small>
                    </div>
                    <div className="provider-payment-amount">
                      <strong>{formatXof(payment.amount_xof)}</strong>
                      <span className={`status-badge ${paymentTone(payment.status)}`}>
                        {PAYMENT_STATUS_LABELS[payment.status]}
                      </span>
                      {payment.status === "PENDING" && payment.checkout_url && (
                        <a href={payment.checkout_url} rel="noopener noreferrer">Reprendre le paiement</a>
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
