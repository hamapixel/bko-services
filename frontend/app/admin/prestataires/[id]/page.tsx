"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import {
  ADMIN_PROVIDER_STATUS_LABELS,
  adminStatusTone,
  apiGet,
  apiMutation,
  formatDate,
  type AdminProvider,
} from "@/lib/admin-api";

type Decision = "APPROVED" | "REJECTED" | "SUSPENDED" | "REOPENED";

export default function AdminProviderDetailPage() {
  const params = useParams<{ id: string }>();
  const [provider, setProvider] = useState<AdminProvider | null>(null);
  const [note, setNote] = useState("");
  const [identityChecked, setIdentityChecked] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    let active = true;
    apiGet<AdminProvider>(`/api/v1/admin/providers/${params.id}/`)
      .then((data) => {
        if (!active) return;
        setProvider(data);
        setIdentityChecked(data.identity_checked);
      })
      .catch((caught) => {
        if (!active) return;
        setError(
          caught instanceof Error ? caught.message : "Dossier introuvable.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [params.id]);

  async function decide(decision: Decision) {
    if (!provider) return;
    if (!note.trim()) {
      setError("Ajoutez une note de contrôle avant la décision.");
      return;
    }

    const labels: Record<Decision, string> = {
      APPROVED: "approuver",
      REJECTED: "refuser",
      SUSPENDED: "suspendre",
      REOPENED: "rouvrir",
    };
    if (!window.confirm(`Confirmer la décision : ${labels[decision]} ce dossier ?`)) {
      return;
    }

    setBusy(true);
    setError("");
    setMessage("");
    try {
      const updated = await apiMutation<AdminProvider>(
        `/api/v1/admin/providers/${provider.id}/review/`,
        "POST",
        {
          decision,
          note: note.trim(),
          identity_checked: identityChecked,
        },
      );
      setProvider(updated);
      setNote("");
      setIdentityChecked(updated.identity_checked);
      setMessage("Décision enregistrée et auditée.");
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Décision impossible.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <div className="skeleton-list">Chargement du dossier…</div>;
  if (!provider) {
    return (
      <div className="empty-state">
        <strong>Dossier indisponible</strong>
        <p>{error}</p>
        <Link className="button-secondary" href="/admin/prestataires">
          Retour
        </Link>
      </div>
    );
  }

  return (
    <main>
      <section className="admin-page-head">
        <div>
          <Link className="back-link" href="/admin/prestataires">
            ← Prestataires
          </Link>
          <p className="page-kicker">Dossier prestataire</p>
          <h1>{provider.display_name}</h1>
          <span className={`status-badge ${adminStatusTone(provider.status)}`}>
            {ADMIN_PROVIDER_STATUS_LABELS[provider.status]}
          </span>
        </div>
      </section>

      {message && <div className="form-success">{message}</div>}
      {error && <div className="inline-error">{error}</div>}

      <div className="detail-grid">
        <div className="detail-main">
          <section className="detail-card">
            <h2>Identité et compte</h2>
            <dl className="detail-list">
              <div><dt>Nom légal</dt><dd>{provider.legal_name}</dd></div>
              <div><dt>Nom public</dt><dd>{provider.display_name}</dd></div>
              <div><dt>Téléphone</dt><dd>{provider.user_phone}</dd></div>
              <div>
                <dt>Téléphone vérifié</dt>
                <dd>{provider.user_phone_verified_at ? "Oui" : "Non"}</dd>
              </div>
              <div><dt>Compte actif</dt><dd>{provider.user_is_active ? "Oui" : "Non"}</dd></div>
              <div>
                <dt>Créé le</dt>
                <dd>{formatDate(provider.created_at)}</dd>
              </div>
            </dl>
            {provider.description && (
              <div className="description-box">
                <strong>Présentation</strong>
                <p>{provider.description}</p>
              </div>
            )}
          </section>

          <section className="detail-card">
            <h2>Métiers et zones</h2>
            <div className="tag-list">
              {provider.trade_details.map((trade) => (
                <span className="provider-tag" key={trade.id}>{trade.name}</span>
              ))}
            </div>
            <div className="tag-list">
              {provider.service_area_details.map((area) => (
                <span className="provider-tag" key={area.id}>
                  {area.name} · {area.commune_name}
                </span>
              ))}
            </div>
          </section>

          <section className="detail-card">
            <h2>Historique des décisions</h2>
            {provider.reviews.length === 0 ? (
              <p className="muted-copy">Aucune décision précédente.</p>
            ) : (
              <div className="timeline">
                {provider.reviews.map((review) => (
                  <div className="timeline-item" key={review.id}>
                    <span className="timeline-dot" />
                    <div>
                      <strong>{review.decision}</strong>
                      <small>{formatDate(review.created_at)}</small>
                      <p>{review.note}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>

        <aside className="detail-side">
          <section className="admin-action-card">
            <p className="page-kicker">Décision</p>
            <h2>Contrôle administratif</h2>

            {provider.status === "PENDING" && (
              <label className="admin-check-row">
                <input
                  checked={identityChecked}
                  type="checkbox"
                  onChange={(event) => setIdentityChecked(event.target.checked)}
                />
                <span>
                  <strong>Identité contrôlée hors ligne</strong>
                  <small>
                    Cochez seulement après le contrôle réel prévu par la procédure.
                  </small>
                </span>
              </label>
            )}

            <label className="field">
              <span>Note de contrôle *</span>
              <textarea
                maxLength={500}
                rows={5}
                value={note}
                onChange={(event) => setNote(event.target.value)}
                placeholder="Motif et éléments vérifiés…"
              />
            </label>

            <div className="admin-action-stack">
              {provider.status === "PENDING" && (
                <>
                  <button
                    className="button-primary"
                    disabled={busy || !identityChecked}
                    type="button"
                    onClick={() => decide("APPROVED")}
                  >
                    Approuver
                  </button>
                  <button
                    className="button-danger-ghost"
                    disabled={busy}
                    type="button"
                    onClick={() => decide("REJECTED")}
                  >
                    Refuser
                  </button>
                </>
              )}
              {provider.status === "VERIFIED" && (
                <button
                  className="button-danger-ghost"
                  disabled={busy}
                  type="button"
                  onClick={() => decide("SUSPENDED")}
                >
                  Suspendre
                </button>
              )}
              {(provider.status === "REJECTED" || provider.status === "SUSPENDED") && (
                <button
                  className="button-primary"
                  disabled={busy}
                  type="button"
                  onClick={() => decide("REOPENED")}
                >
                  Rouvrir le dossier
                </button>
              )}
            </div>
          </section>

          <section className="security-note">
            <strong>Pas de rôle attribué par le frontend</strong>
            <p>
              L’approbation appelle le service backend qui effectue les contrôles,
              change le rôle et écrit l’historique.
            </p>
          </section>
        </aside>
      </div>
    </main>
  );
}
