"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { useAdminSession } from "@/components/admin/admin-shell";
import {
  adminStatusTone,
  apiGet,
  apiMutation,
  formatDate,
  type AdminSubscription,
  type AdminSubscriptionProviderOption,
  type ApiPage,
} from "@/lib/admin-api";
import {
  formatXof,
  type SubscriptionPlan,
} from "@/lib/provider-api";

type AdminPlan = SubscriptionPlan & {
  is_active: boolean;
  display_order: number;
};

export default function AdminSubscriptionsPage() {
  const { refreshOverview } = useAdminSession();
  const [subscriptions, setSubscriptions] = useState<AdminSubscription[]>([]);
  const [providers, setProviders] = useState<AdminSubscriptionProviderOption[]>([]);
  const [plans, setPlans] = useState<AdminPlan[]>([]);
  const [providerId, setProviderId] = useState("");
  const [planId, setPlanId] = useState("");
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function refreshData() {
    const [subscriptionPage, providerPage, planPage] = await Promise.all([
      apiGet<ApiPage<AdminSubscription>>(
        "/api/v1/subscriptions/admin/subscriptions/",
      ),
      apiGet<ApiPage<AdminSubscriptionProviderOption>>(
        "/api/v1/subscriptions/admin/providers/",
      ),
      apiGet<ApiPage<AdminPlan>>("/api/v1/subscriptions/admin/plans/"),
    ]);
    setSubscriptions(subscriptionPage.results);
    setProviders(providerPage.results);
    setPlans(planPage.results);
  }

  useEffect(() => {
    let active = true;
    Promise.all([
      apiGet<ApiPage<AdminSubscription>>(
        "/api/v1/subscriptions/admin/subscriptions/",
      ),
      apiGet<ApiPage<AdminSubscriptionProviderOption>>(
        "/api/v1/subscriptions/admin/providers/",
      ),
      apiGet<ApiPage<AdminPlan>>("/api/v1/subscriptions/admin/plans/"),
    ])
      .then(([subscriptionPage, providerPage, planPage]) => {
        if (!active) return;
        setSubscriptions(subscriptionPage.results);
        setProviders(providerPage.results);
        setPlans(planPage.results);
      })
      .catch((caught) => {
        if (!active) return;
        setError(
          caught instanceof Error
            ? caught.message
            : "Impossible de charger les abonnements.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const availableProviders = useMemo(
    () => providers.filter((provider) => !provider.has_subscription),
    [providers],
  );
  const activePlans = useMemo(
    () => plans.filter((plan) => plan.is_active),
    [plans],
  );

  async function activate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!providerId || !planId) {
      setError("Choisissez un prestataire et un plan.");
      return;
    }

    setBusy(true);
    setError("");
    setMessage("");
    try {
      await apiMutation(
        `/api/v1/subscriptions/admin/providers/${providerId}/activate/`,
        "POST",
        { plan_id: planId, note: note.trim() },
      );
      await Promise.all([refreshData(), refreshOverview()]);
      setProviderId("");
      setPlanId("");
      setNote("");
      setMessage("Abonnement activé.");
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Activation impossible.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function renew(subscription: AdminSubscription) {
    if (
      !window.confirm(
        `Renouveler ${subscription.provider_display_name} avec le même plan ${subscription.plan.name} ?`,
      )
    ) {
      return;
    }
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await apiMutation(
        `/api/v1/subscriptions/admin/subscriptions/${subscription.id}/renew/`,
        "POST",
        { plan_id: subscription.plan.id, note: "Renouvellement depuis l’espace admin." },
      );
      await Promise.all([refreshData(), refreshOverview()]);
      setMessage("Abonnement renouvelé.");
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Renouvellement impossible.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function cancel(subscription: AdminSubscription) {
    const reason = window.prompt(
      `Motif obligatoire pour annuler l’abonnement de ${subscription.provider_display_name} :`,
    );
    if (!reason?.trim()) return;

    setBusy(true);
    setError("");
    setMessage("");
    try {
      await apiMutation(
        `/api/v1/subscriptions/admin/subscriptions/${subscription.id}/cancel/`,
        "POST",
        { note: reason.trim() },
      );
      await Promise.all([refreshData(), refreshOverview()]);
      setMessage("Abonnement annulé.");
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Annulation impossible.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <section className="admin-page-head">
        <div>
          <p className="page-kicker">Abonnements</p>
          <h1>Plans et droits prestataires</h1>
          <p>
            Activation, renouvellement et annulation passent exclusivement par
            les services backend audités.
          </p>
        </div>
      </section>

      {message && <div className="form-success">{message}</div>}
      {error && <div className="inline-error">{error}</div>}
      {loading && <div className="skeleton-list">Chargement…</div>}

      {!loading && (
        <>
          <section className="detail-card admin-activation-card">
            <p className="page-kicker">Activation manuelle</p>
            <h2>Attribuer un plan</h2>
            <form className="admin-activation-form" onSubmit={activate}>
              <label className="field">
                <span>Prestataire vérifié sans abonnement</span>
                <select
                  required
                  value={providerId}
                  onChange={(event) => setProviderId(event.target.value)}
                >
                  <option value="">Choisir</option>
                  {availableProviders.map((provider) => (
                    <option value={provider.id} key={provider.id}>
                      {provider.display_name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Plan actif</span>
                <select
                  required
                  value={planId}
                  onChange={(event) => setPlanId(event.target.value)}
                >
                  <option value="">Choisir</option>
                  {activePlans.map((plan) => (
                    <option value={plan.id} key={plan.id}>
                      {plan.name} · {formatXof(plan.price_xof)} · {plan.duration_days} j
                    </option>
                  ))}
                </select>
              </label>
              <label className="field admin-note-field">
                <span>Note (facultatif)</span>
                <input
                  maxLength={500}
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  placeholder="Motif ou référence interne"
                />
              </label>
              <button className="button-primary" disabled={busy} type="submit">
                {busy ? "Traitement…" : "Activer"}
              </button>
            </form>
          </section>

          <section className="content-section admin-section-gap">
            <div className="section-heading">
              <div>
                <p className="page-kicker">Plans</p>
                <h2>Catalogue configuré</h2>
              </div>
            </div>
            <div className="provider-plan-grid">
              {plans.map((plan) => (
                <article className="provider-plan-card" key={plan.id}>
                  <div>
                    <span className="request-meta">
                      {plan.is_active ? "Actif" : "Inactif"} · {plan.duration_days} jours
                    </span>
                    <h3>{plan.name}</h3>
                    <p>{plan.description || "Sans description."}</p>
                  </div>
                  <strong className="provider-plan-price">
                    {formatXof(plan.price_xof)}
                  </strong>
                  <div className="subscription-entitlements">
                    <span>{plan.can_receive_requests ? "✓" : "×"} Demandes</span>
                    <span>{plan.can_receive_urgent_requests ? "✓" : "×"} Urgences</span>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className="content-section admin-section-gap">
            <div className="section-heading">
              <div>
                <p className="page-kicker">Prestataires</p>
                <h2>Abonnements existants</h2>
              </div>
            </div>

            {subscriptions.length === 0 ? (
              <div className="empty-state compact">
                <strong>Aucun abonnement</strong>
                <p>Aucun prestataire n’a encore d’abonnement.</p>
              </div>
            ) : (
              <div className="admin-list">
                {subscriptions.map((subscription) => (
                  <article className="admin-list-card admin-subscription-row" key={subscription.id}>
                    <div>
                      <span className="request-meta">{subscription.plan.name}</span>
                      <h3>{subscription.provider_display_name}</h3>
                      <p>
                        {formatDate(subscription.starts_at)} → {formatDate(subscription.ends_at)}
                      </p>
                    </div>
                    <div className="admin-list-meta">
                      <span className={`status-badge ${adminStatusTone(subscription.status)}`}>
                        {subscription.status}
                      </span>
                      <div className="admin-inline-actions">
                        <button
                          className="button-secondary"
                          disabled={busy}
                          type="button"
                          onClick={() => renew(subscription)}
                        >
                          Renouveler
                        </button>
                        {subscription.status === "ACTIVE" && (
                          <button
                            className="button-danger-ghost"
                            disabled={busy}
                            type="button"
                            onClick={() => cancel(subscription)}
                          >
                            Annuler
                          </button>
                        )}
                      </div>
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
