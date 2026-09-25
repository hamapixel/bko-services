"use client";

import { useEffect, useState } from "react";

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

export default function ProviderSubscriptionPage() {
  const [subscription, setSubscription] = useState<ProviderSubscription | null>(null);
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [payments, setPayments] = useState<PaymentTransaction[]>([]);
  const [waveAvailable, setWaveAvailable] = useState(false);
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
  }

  useEffect(() => {
    let active = true;

    Promise.all([
      apiGet<{ subscription: ProviderSubscription | null }>(
        "/api/v1/subscriptions/me/",
      ),
      apiGet<ApiPage<SubscriptionPlan>>("/api/v1/subscriptions/plans/"),
      apiGet<ApiPage<PaymentTransaction>>("/api/v1/payments/transactions/"),
      apiGet<{ wave: boolean; orange_money: boolean }>("/api/v1/payments/methods/"),
    ])
      .then(([subscriptionPayload, planPage, paymentPage, methods]) => {
        if (!active) return;
        setSubscription(subscriptionPayload.subscription);
        setPlans(planPage.results);
        setPayments(paymentPage.results);
        setWaveAvailable(methods.wave);
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

  async function payWithWave(plan: SubscriptionPlan) {
    if (plan.price_xof === 0) {
      setError(
        "Ce plan gratuit nécessite une activation administrative.",
      );
      return;
    }

    if (
      !window.confirm(
        `Payer ${formatXof(plan.price_xof)} avec Wave pour le plan ${plan.name} ? Vous serez redirigé vers Wave.`,
      )
    ) {
      return;
    }

    setBusyPlan(plan.id);
    setError("");
    setMessage("");
    try {
      const key = `web-${crypto.randomUUID()}`;
      const payment = await apiMutation<PaymentTransaction>(
        "/api/v1/payments/wave/checkout/",
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
      if (!payment.checkout_url) throw new Error("Lien de paiement Wave indisponible.");
      window.location.assign(payment.checkout_url);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Impossible de lancer le paiement Wave.",
      );
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
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Actualisation impossible.",
      );
    }
  }

  return (
    <main>
      <section className="provider-page-head">
        <div>
          <p className="page-kicker">Abonnement</p>
          <h1>Plans et paiements</h1>
          <p>
            Votre droit à recevoir de nouvelles offres dépend d’un abonnement
            effectif. Les interventions déjà attribuées ne sont pas interrompues
            par une expiration ultérieure.
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
                  <div className="subscription-entitlements">
                    <span>
                      {subscription.plan.can_receive_requests ? "✓" : "×"} Demandes normales
                    </span>
                    <span>
                      {subscription.plan.can_receive_urgent_requests ? "✓" : "×"} Demandes urgentes
                    </span>
                    <span>{subscription.plan.max_active_jobs === null ? "Interventions simultanées illimitées" : `${subscription.plan.max_active_jobs} intervention${subscription.plan.max_active_jobs > 1 ? "s" : ""} en cours à la fois`}</span>
                  </div>
                </>
              ) : (
                <>
                  <h2>Aucun abonnement</h2>
                  <p>
                    Vous pouvez consulter votre espace, mais aucune nouvelle offre
                    ne doit être reçue sans droit actif.
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
              {plans.map((plan) => (
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
                    disabled={busyPlan !== null || plan.price_xof === 0 || !waveAvailable}
                    type="button"
                    onClick={() => payWithWave(plan)}
                  >
                    {busyPlan === plan.id
                      ? "Préparation…"
                      : plan.price_xof === 0
                        ? "Activation administrative"
                        : waveAvailable ? "Payer avec Wave" : "Paiement bientôt disponible"}
                  </button>
                </article>
              ))}
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
              <strong>{waveAvailable ? "Paiement Wave" : "Paiement mobile bientôt disponible"}</strong>
              <p>
                {waveAvailable
                  ? "Après paiement sur Wave, actualisez vos statuts. Seule la confirmation sécurisée de Wave active votre abonnement."
                  : "La connexion du compte marchand Wave est en cours. Aucun paiement n’est encaissé sur cette page pour le moment."}
                {" "}Orange Money sera proposé après activation du compte marchand et de son intégration.
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
                        <a href={payment.checkout_url} rel="noopener noreferrer">Reprendre sur Wave</a>
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
