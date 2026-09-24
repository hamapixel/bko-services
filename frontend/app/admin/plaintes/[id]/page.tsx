"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { useAdminSession } from "@/components/admin/admin-shell";
import {
  COMPLAINT_CATEGORY_LABELS,
  COMPLAINT_STATUS_LABELS,
  adminStatusTone,
  apiGet,
  apiMutation,
  formatDate,
  type AdminComplaint,
} from "@/lib/admin-api";

type Target = "UNDER_REVIEW" | "RESOLVED" | "REJECTED";

export default function AdminComplaintDetailPage() {
  const params = useParams<{ id: string }>();
  const { refreshOverview } = useAdminSession();
  const [item, setItem] = useState<AdminComplaint | null>(null);
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    let active = true;
    apiGet<AdminComplaint>(`/api/v1/complaints/admin/${params.id}/`)
      .then((data) => {
        if (active) setItem(data);
      })
      .catch((caught) => {
        if (!active) return;
        setError(caught instanceof Error ? caught.message : "Plainte introuvable.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [params.id]);

  async function transition(status: Target) {
    if (!item) return;
    const isFinal = status === "RESOLVED" || status === "REJECTED";
    if (isFinal && !note.trim()) {
      setError("Une note de décision est obligatoire pour clôturer la plainte.");
      return;
    }

    setBusy(true);
    setError("");
    setMessage("");
    try {
      const updated = await apiMutation<AdminComplaint>(
        `/api/v1/complaints/admin/${item.id}/transition/`,
        "POST",
        { status, note: note.trim() },
      );
      setItem(updated);
      setNote("");
      setMessage("Transition enregistrée.");
      await refreshOverview();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Transition impossible.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <div className="skeleton-list">Chargement…</div>;
  if (!item) {
    return (
      <div className="empty-state">
        <strong>Plainte indisponible</strong>
        <p>{error}</p>
        <Link className="button-secondary" href="/admin/plaintes">Retour</Link>
      </div>
    );
  }

  const active = item.status === "OPEN" || item.status === "UNDER_REVIEW";

  return (
    <main>
      <section className="admin-page-head">
        <div>
          <Link className="back-link" href="/admin/plaintes">← Plaintes</Link>
          <p className="page-kicker">{COMPLAINT_CATEGORY_LABELS[item.category]}</p>
          <h1>Plainte sur l’intervention</h1>
          <span className={`status-badge ${adminStatusTone(item.status)}`}>
            {COMPLAINT_STATUS_LABELS[item.status]}
          </span>
        </div>
        <Link className="button-secondary" href={`/admin/demandes/${item.service_request_id}`}>
          Voir la demande
        </Link>
      </section>

      {message && <div className="form-success">{message}</div>}
      {error && <div className="inline-error">{error}</div>}

      <div className="detail-grid">
        <div className="detail-main">
          <section className="detail-card">
            <h2>Signalement</h2>
            <dl className="detail-list">
              <div><dt>Reporter</dt><dd>{item.reporter_role}</dd></div>
              <div><dt>Ancien statut demande</dt><dd>{item.previous_request_status}</dd></div>
              <div><dt>Créée le</dt><dd>{formatDate(item.created_at)}</dd></div>
              <div><dt>Résolue le</dt><dd>{item.resolved_at ? formatDate(item.resolved_at) : "—"}</dd></div>
            </dl>
            <div className="description-box">
              <strong>Description</strong>
              <p>{item.description}</p>
            </div>
            {item.resolution_note && (
              <div className="description-box admin-resolution-box">
                <strong>Décision finale</strong>
                <p>{item.resolution_note}</p>
              </div>
            )}
          </section>

          <section className="detail-card">
            <h2>Historique</h2>
            <div className="timeline">
              {item.status_history.map((history, index) => (
                <div className="timeline-item" key={`${history.created_at}-${index}`}>
                  <span className="timeline-dot" />
                  <div>
                    <strong>{COMPLAINT_STATUS_LABELS[history.new_status]}</strong>
                    <small>{formatDate(history.created_at)}</small>
                    {history.note && <p>{history.note}</p>}
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>

        <aside className="detail-side">
          {active && (
            <section className="admin-action-card">
              <p className="page-kicker">Traitement</p>
              <h2>Décision administrative</h2>
              <label className="field">
                <span>Note</span>
                <textarea
                  maxLength={1000}
                  rows={5}
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  placeholder="Analyse et décision…"
                />
              </label>
              <div className="admin-action-stack">
                {item.status === "OPEN" && (
                  <button
                    className="button-secondary"
                    disabled={busy}
                    type="button"
                    onClick={() => transition("UNDER_REVIEW")}
                  >
                    Prendre en charge
                  </button>
                )}
                <button
                  className="button-primary"
                  disabled={busy}
                  type="button"
                  onClick={() => transition("RESOLVED")}
                >
                  Résoudre
                </button>
                <button
                  className="button-danger-ghost"
                  disabled={busy}
                  type="button"
                  onClick={() => transition("REJECTED")}
                >
                  Rejeter
                </button>
              </div>
            </section>
          )}
          <section className="security-note">
            <strong>Restauration contrôlée</strong>
            <p>
              Une décision finale restaure côté serveur le statut de
              l’intervention enregistré avant le litige.
            </p>
          </section>
        </aside>
      </div>
    </main>
  );
}
