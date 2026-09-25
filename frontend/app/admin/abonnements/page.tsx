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

type PlanForm = {
  code: string;
  name: string;
  description: string;
  price_xof: string;
  duration_days: string;
  can_receive_requests: boolean;
  can_receive_urgent_requests: boolean;
  is_active: boolean;
  display_order: string;
};

const EMPTY_PLAN: PlanForm = {
  code: "",
  name: "",
  description: "",
  price_xof: "",
  duration_days: "30",
  can_receive_requests: true,
  can_receive_urgent_requests: false,
  is_active: false,
  display_order: "10",
};

const MONTHLY_DRAFTS = [
  { code: "mensuel-essentiel", name: "Mensuel Essentiel", display_order: 10 },
  { code: "mensuel-plus", name: "Mensuel Plus", display_order: 20 },
  { code: "mensuel-pro", name: "Mensuel Pro", display_order: 30 },
];

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
  const [creatingTrial, setCreatingTrial] = useState(false);
  const [creatingDrafts, setCreatingDrafts] = useState(false);
  const [editingPlanId, setEditingPlanId] = useState<string | null>(null);
  const [planForm, setPlanForm] = useState<PlanForm>(EMPTY_PLAN);
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
  const trialPlan = plans.find((plan) => plan.code === "essai-14j");
  const legacyTrial = plans.find((plan) => plan.code === "essai-7j" && plan.is_active);
  const missingMonthlyDrafts = MONTHLY_DRAFTS.filter(
    (draft) => !plans.some((plan) => plan.code === draft.code),
  );

  async function createTrialPlan() {
    setCreatingTrial(true);
    setError("");
    setMessage("");
    try {
      const plan = trialPlan ?? await apiMutation<AdminPlan>(
        "/api/v1/subscriptions/admin/plans/", "POST", {
          code: "essai-14j",
          name: "Essai 14 jours",
          description: "Offres normales et urgentes pendant 14 jours après activation par l’administration.",
          price_xof: 0, duration_days: 14,
          can_receive_requests: true, can_receive_urgent_requests: true,
          is_active: true, display_order: 0,
        },
      );
      if (!plan.is_active) {
        await apiMutation(`/api/v1/subscriptions/admin/plans/${plan.id}/`, "PATCH", { is_active: true });
      }
      if (legacyTrial) {
        await apiMutation(
          `/api/v1/subscriptions/admin/plans/${legacyTrial.id}/`,
          "PATCH", { is_active: false },
        );
      }
      await refreshData();
      setPlanId(plan.id);
      setMessage("Essai de 14 jours disponible. Sélectionnez un prestataire vérifié pour l’activer.");
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Création du plan d’essai impossible.",
      );
    } finally {
      setCreatingTrial(false);
    }
  }

  async function createMonthlyDrafts() {
    setCreatingDrafts(true);
    setError("");
    setMessage("");
    try {
      for (const draft of missingMonthlyDrafts) {
        await apiMutation("/api/v1/subscriptions/admin/plans/", "POST", {
          ...draft, description: "Prix et droits à configurer avant publication.",
          price_xof: 0, duration_days: 30,
          can_receive_requests: true, can_receive_urgent_requests: false,
          is_active: false,
        });
      }
      await refreshData();
      setMessage("Modèles mensuels prêts. Modifiez chaque plan, fixez son prix, puis activez-le.");
    } catch (caught) {
      await refreshData().catch(() => undefined);
      setError(caught instanceof Error ? caught.message : "Création des modèles impossible.");
    } finally {
      setCreatingDrafts(false);
    }
  }

  function editPlan(plan: AdminPlan) {
    setEditingPlanId(plan.id);
    setPlanForm({
      code: plan.code, name: plan.name, description: plan.description,
      price_xof: String(plan.price_xof), duration_days: String(plan.duration_days),
      can_receive_requests: plan.can_receive_requests,
      can_receive_urgent_requests: plan.can_receive_urgent_requests,
      is_active: plan.is_active, display_order: String(plan.display_order),
    });
    document.getElementById("plan-editor")?.scrollIntoView({ behavior: "smooth" });
  }

  async function savePlan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const price = Number(planForm.price_xof);
    const duration = Number(planForm.duration_days);
    const order = Number(planForm.display_order);
    if (!Number.isSafeInteger(price) || price < 0 || !Number.isInteger(duration) || duration < 1 || !Number.isInteger(order) || order < 0) {
      setError("Vérifiez le prix, la durée et l’ordre d’affichage.");
      return;
    }
    if (planForm.can_receive_urgent_requests && !planForm.can_receive_requests) {
      setError("Les urgences nécessitent aussi le droit aux demandes normales.");
      return;
    }
    if (planForm.code.startsWith("mensuel-") && planForm.is_active && price === 0) {
      setError("Fixez un prix supérieur à 0 FCFA avant de publier un plan mensuel.");
      return;
    }
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const payload = {
        ...(editingPlanId ? {} : { code: planForm.code.trim() }),
        name: planForm.name.trim(), description: planForm.description.trim(),
        price_xof: price, duration_days: duration,
        can_receive_requests: planForm.can_receive_requests,
        can_receive_urgent_requests: planForm.can_receive_urgent_requests,
        is_active: planForm.is_active, display_order: order,
      };
      await apiMutation(
        editingPlanId
          ? `/api/v1/subscriptions/admin/plans/${editingPlanId}/`
          : "/api/v1/subscriptions/admin/plans/",
        editingPlanId ? "PATCH" : "POST", payload,
      );
      await refreshData();
      setEditingPlanId(null);
      setPlanForm(EMPTY_PLAN);
      setMessage("Plan enregistré. Les plans actifs sont visibles par les prestataires.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Enregistrement du plan impossible.");
    } finally {
      setBusy(false);
    }
  }

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
          <section className="detail-card admin-section-gap">
            <p className="page-kicker">Essai gratuit</p>
            <h2>Essai de 14 jours</h2>
            <p>
              14 jours à 0 FCFA, pour les demandes normales et urgentes. Seul un
              administrateur peut l’activer pour un prestataire vérifié. Aucun
              paiement n’est enregistré pour cet essai.
            </p>
            {legacyTrial && <p className="muted-copy">L’ancien essai de 7 jours sera désactivé pour les nouvelles activations. Les essais déjà attribués gardent leur date de fin.</p>}
            {trialPlan?.is_active && !legacyTrial ? (
              <p className="muted-copy">Le plan d’essai de 14 jours est actif.</p>
            ) : (
              <button
                className="button-secondary"
                disabled={creatingTrial || busy}
                type="button"
                onClick={createTrialPlan}
              >
                {creatingTrial ? "Préparation…" : "Activer le nouvel essai de 14 jours"}
              </button>
            )}
          </section>

          <section className="detail-card admin-section-gap" id="plan-editor">
            <p className="page-kicker">Catalogue</p>
            <h2>{editingPlanId ? "Modifier un plan" : "Créer un plan"}</h2>
            <p>Les trois modèles mensuels durent 30 jours. Leur prix est à définir avant publication.</p>
            {missingMonthlyDrafts.length > 0 && (
              <button className="button-secondary" type="button" disabled={creatingDrafts || busy} onClick={createMonthlyDrafts}>
                {creatingDrafts ? "Création…" : "Créer les modèles mensuels manquants"}
              </button>
            )}
            <form className="admin-plan-form" onSubmit={savePlan}>
              <label className="field">
                <span>Code unique</span>
                <input required maxLength={50} pattern="[a-z0-9]+(?:[-_][a-z0-9]+)*" readOnly={editingPlanId !== null} value={planForm.code} onChange={(event) => setPlanForm({ ...planForm, code: event.target.value })} placeholder="mensuel-essentiel" />
              </label>
              <label className="field">
                <span>Nom du plan</span>
                <input required maxLength={120} value={planForm.name} onChange={(event) => setPlanForm({ ...planForm, name: event.target.value })} placeholder="Mensuel Essentiel" />
              </label>
              <label className="field">
                <span>Prix (FCFA)</span>
                <input required type="number" min="0" step="1" value={planForm.price_xof} onChange={(event) => setPlanForm({ ...planForm, price_xof: event.target.value })} placeholder="À fixer" />
              </label>
              <label className="field">
                <span>Durée (jours)</span>
                <input required type="number" min="1" max="65535" step="1" value={planForm.duration_days} onChange={(event) => setPlanForm({ ...planForm, duration_days: event.target.value })} />
              </label>
              <label className="field">
                <span>Demandes normales</span>
                <select value={planForm.can_receive_requests ? "yes" : "no"} onChange={(event) => setPlanForm({ ...planForm, can_receive_requests: event.target.value === "yes", can_receive_urgent_requests: event.target.value === "yes" && planForm.can_receive_urgent_requests })}>
                  <option value="yes">Oui</option><option value="no">Non</option>
                </select>
              </label>
              <label className="field">
                <span>Demandes urgentes</span>
                <select value={planForm.can_receive_urgent_requests ? "yes" : "no"} onChange={(event) => setPlanForm({ ...planForm, can_receive_urgent_requests: event.target.value === "yes", can_receive_requests: event.target.value === "yes" || planForm.can_receive_requests })}>
                  <option value="no">Non</option><option value="yes">Oui</option>
                </select>
              </label>
              <label className="field">
                <span>Statut</span>
                <select value={planForm.is_active ? "yes" : "no"} onChange={(event) => setPlanForm({ ...planForm, is_active: event.target.value === "yes" })}>
                  <option value="no">Brouillon (invisible)</option><option value="yes">Actif (visible)</option>
                </select>
              </label>
              <label className="field">
                <span>Ordre d’affichage</span>
                <input required type="number" min="0" max="65535" step="1" value={planForm.display_order} onChange={(event) => setPlanForm({ ...planForm, display_order: event.target.value })} />
              </label>
              <label className="field admin-plan-description">
                <span>Description</span>
                <textarea maxLength={1000} rows={3} value={planForm.description} onChange={(event) => setPlanForm({ ...planForm, description: event.target.value })} placeholder="Expliquez ce que comprend le plan." />
              </label>
              <div className="admin-plan-actions">
                <button className="button-primary" disabled={busy || creatingDrafts} type="submit">{busy ? "Enregistrement…" : editingPlanId ? "Enregistrer les modifications" : "Créer le plan"}</button>
                {editingPlanId && <button className="button-secondary" type="button" onClick={() => { setEditingPlanId(null); setPlanForm(EMPTY_PLAN); }}>Annuler</button>}
              </div>
            </form>
          </section>

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
            <p className="muted-copy">
              Cette activation manuelle ne confirme aucun paiement. Utilisez-la
              pour un essai gratuit ou après vérification d’un paiement reçu hors plateforme.
            </p>
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
                  <button className="button-secondary" type="button" onClick={() => editPlan(plan)}>Modifier le plan</button>
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
