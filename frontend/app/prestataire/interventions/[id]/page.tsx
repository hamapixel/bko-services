"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import {
  apiGet,
  apiMutation,
  formatDate,
  nextProviderStatus,
  PROVIDER_ACTION_LABELS,
  STATUS_LABELS,
  statusTone,
  type ProviderIntervention,
} from "@/lib/provider-api";

export default function ProviderInterventionDetailPage() {
  const params = useParams<{ id: string }>();
  const [intervention, setIntervention] = useState<ProviderIntervention | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    let active = true;

    apiGet<ProviderIntervention>(
      `/api/v1/providers/interventions/${params.id}/`,
    )
      .then((data) => {
        if (active) setIntervention(data);
      })
      .catch((caught) => {
        if (!active) return;
        setError(
          caught instanceof Error
            ? caught.message
            : "Intervention introuvable.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [params.id]);

  const nextStatus = useMemo(
    () => (intervention ? nextProviderStatus(intervention.status) : null),
    [intervention],
  );

  async function advance() {
    if (!intervention || !nextStatus) return;

    const label = PROVIDER_ACTION_LABELS[nextStatus] ?? "Continuer";
    if (!window.confirm(`${label} ? Cette étape sera enregistrée par le serveur.`)) {
      return;
    }

    setBusy(true);
    setError("");
    setMessage("");

    try {
      const updated = await apiMutation<ProviderIntervention>(
        `/api/v1/providers/interventions/${intervention.id}/transition/`,
        "POST",
        { status: nextStatus },
      );
      setIntervention(updated);
      setMessage(`Étape enregistrée : ${STATUS_LABELS[updated.status]}.`);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Impossible de faire avancer l’intervention.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return <div className="skeleton-list">Chargement de l’intervention…</div>;
  }

  if (error && !intervention) {
    return (
      <div className="empty-state">
        <strong>Intervention introuvable</strong>
        <p>{error}</p>
        <Link className="button-secondary" href="/prestataire/interventions">
          Retour aux interventions
        </Link>
      </div>
    );
  }

  if (!intervention) return null;

  const terminalProvider =
    intervention.status === "PROVIDER_COMPLETED" ||
    intervention.status === "CLIENT_CONFIRMED";

  return (
    <main>
      <section className="provider-page-head">
        <div>
          <Link className="back-link" href="/prestataire/interventions">
            ← Mes interventions
          </Link>
          <p className="page-kicker">
            {intervention.trade_name} · {intervention.commune_name}
          </p>
          <h1>{intervention.title}</h1>
          <div className="detail-badges">
            <span className={`status-badge ${statusTone(intervention.status)}`}>
              {STATUS_LABELS[intervention.status]}
            </span>
            {intervention.priority === "URGENT" && (
              <span className="urgent-label">Urgente</span>
            )}
          </div>
        </div>
      </section>

      {message && <div className="form-success">{message}</div>}
      {error && <div className="inline-error">{error}</div>}

      <div className="detail-grid">
        <div className="detail-main">
          <section className="detail-card">
            <h2>Informations d’intervention</h2>
            <dl className="detail-list">
              <div>
                <dt>Métier</dt>
                <dd>{intervention.trade_name}</dd>
              </div>
              <div>
                <dt>Quartier</dt>
                <dd>{intervention.neighborhood_name}, {intervention.commune_name}</dd>
              </div>
              <div>
                <dt>Adresse précise</dt>
                <dd>{intervention.address_detail}</dd>
              </div>
              <div>
                <dt>Créée le</dt>
                <dd>{formatDate(intervention.created_at)}</dd>
              </div>
            </dl>
            <div className="description-box">
              <strong>Description du client</strong>
              <p>{intervention.description}</p>
            </div>
          </section>

          <section className="detail-card">
            <div className="section-heading">
              <div>
                <p className="page-kicker">Historique</p>
                <h2>Progression</h2>
              </div>
            </div>
            <div className="timeline">
              {intervention.status_history.map((item, index) => (
                <div className="timeline-item" key={`${item.created_at}-${index}`}>
                  <span className="timeline-dot" />
                  <div>
                    <strong>{STATUS_LABELS[item.new_status]}</strong>
                    <small>{formatDate(item.created_at)}</small>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {nextStatus && (
            <section className="action-card provider-progress-card">
              <div>
                <p className="page-kicker">Étape suivante</p>
                <h2>{PROVIDER_ACTION_LABELS[nextStatus]}</h2>
                <p>
                  BKO Services vérifie que la transition est autorisée avant de
                  modifier l’état de l’intervention.
                </p>
              </div>
              <button
                className="button-primary"
                disabled={busy}
                type="button"
                onClick={advance}
              >
                {busy ? "Enregistrement…" : PROVIDER_ACTION_LABELS[nextStatus]}
              </button>
            </section>
          )}

          {intervention.status === "PROVIDER_COMPLETED" && (
            <div className="provider-waiting-client">
              <strong>Votre partie est terminée.</strong>
              <p>
                Le client doit maintenant confirmer la fin. Vous ne pouvez pas
                effectuer cette confirmation à sa place.
              </p>
            </div>
          )}

          {intervention.status === "CLIENT_CONFIRMED" && (
            <div className="review-done">
              ✓ Intervention confirmée par le client.
            </div>
          )}
        </div>

        <aside className="detail-side">
          <section className="provider-card">
            <p className="page-kicker">Client attribué</p>
            <div className="provider-avatar">C</div>
            <h2>Contact client</h2>
            <p>
              Ces coordonnées ne sont disponibles que parce que cette
              intervention vous a été attribuée.
            </p>
            <a
              className="button-secondary button-wide"
              href={`tel:${intervention.client_phone}`}
            >
              Appeler {intervention.client_phone}
            </a>
          </section>

          <section className="security-note">
            <strong>Ordre obligatoire</strong>
            <p>
              Acceptée → En route → Arrivé → En cours → Terminée prestataire.
              Une étape ne peut pas être sautée.
            </p>
          </section>

          {terminalProvider && (
            <Link className="button-secondary button-wide" href="/prestataire/avis">
              Voir mes avis
            </Link>
          )}
        </aside>
      </div>
    </main>
  );
}
