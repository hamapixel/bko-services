"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import {
  apiGet,
  apiMutation,
  formatDate,
  STATUS_LABELS,
  statusTone,
  type Review,
  type ServiceRequest,
} from "@/lib/client-api";

export default function ClientRequestDetailPage() {
  const params = useParams<{ id: string }>();
  const requestId = params.id;
  const [request, setRequest] = useState<ServiceRequest | null>(null);
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function loadRequest() {
    const data = await apiGet<ServiceRequest>(
      `/api/v1/requests/${requestId}/`,
    );
    setRequest(data);
  }

  useEffect(() => {
    let active = true;
    apiGet<ServiceRequest>(`/api/v1/requests/${requestId}/`)
      .then((data) => {
        if (active) setRequest(data);
      })
      .catch((caught) => {
        if (!active) return;
        setError(
          caught instanceof Error
            ? caught.message
            : "Impossible de charger cette demande.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [requestId]);

  async function confirmCompletion() {
    if (
      !window.confirm(
        "Confirmer que l’intervention est réellement terminée ?",
      )
    ) {
      return;
    }

    setBusy(true);
    setError("");
    setMessage("");
    try {
      const updated = await apiMutation<ServiceRequest>(
        `/api/v1/requests/${requestId}/confirm/`,
        "POST",
        {},
      );
      setRequest(updated);
      setMessage("Fin de l’intervention confirmée.");
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Confirmation impossible.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function submitReview() {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await apiMutation<Review>(
        `/api/v1/requests/${requestId}/review/`,
        "POST",
        { rating, comment: comment.trim() },
      );
      await loadRequest();
      setMessage("Merci, votre avis a bien été enregistré.");
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Avis impossible à envoyer.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return <div className="skeleton-list">Chargement de la demande…</div>;
  }

  if (error && !request) {
    return (
      <div className="empty-state">
        <strong>Demande introuvable</strong>
        <p>{error}</p>
        <Link className="button-secondary" href="/client/demandes">
          Retour aux demandes
        </Link>
      </div>
    );
  }

  if (!request) return null;

  return (
    <main>
      <section className="client-page-head detail-head">
        <div>
          <Link className="back-link" href="/client/demandes">
            ← Mes demandes
          </Link>
          <p className="page-kicker">
            {request.trade_name} · {request.commune_name}
          </p>
          <h1>{request.title}</h1>
          <div className="detail-badges">
            <span className={`status-badge ${statusTone(request.status)}`}>
              {STATUS_LABELS[request.status]}
            </span>
            {request.priority === "URGENT" && (
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
            <h2>Détails de la demande</h2>
            <dl className="detail-list">
              <div>
                <dt>Métier</dt>
                <dd>{request.trade_name}</dd>
              </div>
              <div>
                <dt>Quartier</dt>
                <dd>
                  {request.neighborhood_name}, {request.commune_name}
                </dd>
              </div>
              <div>
                <dt>Adresse</dt>
                <dd>{request.address_detail}</dd>
              </div>
              <div>
                <dt>Créée le</dt>
                <dd>{formatDate(request.created_at)}</dd>
              </div>
            </dl>
            <div className="description-box">
              <strong>Description</strong>
              <p>{request.description}</p>
            </div>
          </section>

          <section className="detail-card">
            <div className="section-heading">
              <div>
                <p className="page-kicker">Suivi</p>
                <h2>Progression</h2>
              </div>
            </div>

            <div className="timeline">
              {request.status_history.map((item, index) => (
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

          {request.status === "PROVIDER_COMPLETED" && (
            <section className="action-card success-action">
              <div>
                <p className="page-kicker">Action requise</p>
                <h2>Le prestataire indique avoir terminé.</h2>
                <p>
                  Confirmez seulement si l’intervention est réellement terminée
                  et conforme à ce qui a été réalisé.
                </p>
              </div>
              <button
                className="button-primary"
                disabled={busy}
                type="button"
                onClick={confirmCompletion}
              >
                Confirmer la fin
              </button>
            </section>
          )}

          {request.status === "CLIENT_CONFIRMED" && !request.has_review && (
            <section className="detail-card">
              <p className="page-kicker">Votre avis</p>
              <h2>Comment s’est passée l’intervention ?</h2>
              <div className="rating-row" aria-label="Note">
                {[1, 2, 3, 4, 5].map((value) => (
                  <button
                    className={value <= rating ? "star active" : "star"}
                    key={value}
                    type="button"
                    aria-label={`${value} étoile${value > 1 ? "s" : ""}`}
                    onClick={() => setRating(value)}
                  >
                    ★
                  </button>
                ))}
              </div>
              <label className="field">
                <span>Commentaire (facultatif)</span>
                <textarea
                  maxLength={1000}
                  rows={4}
                  value={comment}
                  onChange={(event) => setComment(event.target.value)}
                  placeholder="Décrivez votre expérience…"
                />
              </label>
              <button
                className="button-primary"
                disabled={busy}
                type="button"
                onClick={submitReview}
              >
                Publier mon avis
              </button>
            </section>
          )}

          {request.status === "CLIENT_CONFIRMED" && request.has_review && (
            <div className="review-done">✓ Votre avis a déjà été enregistré.</div>
          )}
        </div>

        <aside className="detail-side">
          <section className="provider-card">
            <p className="page-kicker">Prestataire</p>
            {request.assigned_provider_display_name ? (
              <>
                <div className="provider-avatar">P</div>
                <h2>{request.assigned_provider_display_name}</h2>
                <p>Prestataire attribué à cette demande.</p>
                {request.assigned_provider_phone && (
                  <a
                    className="button-secondary button-wide"
                    href={`tel:${request.assigned_provider_phone}`}
                  >
                    Appeler {request.assigned_provider_phone}
                  </a>
                )}
              </>
            ) : (
              <>
                <h2>Recherche en cours</h2>
                <p>
                  Les coordonnées privées apparaîtront seulement après
                  attribution d’un prestataire.
                </p>
              </>
            )}
          </section>

          <section className="security-note">
            <strong>Vos données restent privées</strong>
            <p>
              BKO Services n’affiche votre adresse précise qu’au prestataire
              attribué à l’intervention.
            </p>
          </section>
        </aside>
      </div>
    </main>
  );
}
