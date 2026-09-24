"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { useAdminSession } from "@/components/admin/admin-shell";
import {
  apiGet,
  apiMutation,
  formatDate,
  type AdminRequestDetail,
} from "@/lib/admin-api";
import { STATUS_LABELS, statusTone } from "@/lib/client-api";

type DispatchResponse = {
  offers_created: number;
  request: AdminRequestDetail;
};

export default function AdminRequestDetailPage() {
  const params = useParams<{ id: string }>();
  const { overview, refreshOverview } = useAdminSession();
  const [item, setItem] = useState<AdminRequestDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    let active = true;
    apiGet<AdminRequestDetail>(`/api/v1/admin/requests/${params.id}/`)
      .then((data) => {
        if (active) setItem(data);
      })
      .catch((caught) => {
        if (!active) return;
        setError(
          caught instanceof Error ? caught.message : "Demande introuvable.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [params.id]);

  async function dispatch() {
    if (!item) return;
    if (!window.confirm("Lancer la recherche de prestataires compatibles ?")) {
      return;
    }

    setBusy(true);
    setError("");
    setMessage("");
    try {
      const result = await apiMutation<DispatchResponse>(
        `/api/v1/admin/requests/${item.id}/dispatch/`,
        "POST",
        {},
      );
      setItem(result.request);
      setMessage(
        result.offers_created > 0
          ? `${result.offers_created} offre(s) créée(s).`
          : "Aucun prestataire compatible disponible pour le moment.",
      );
      await refreshOverview();
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Matching impossible.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <div className="skeleton-list">Chargement…</div>;
  if (!item) {
    return (
      <div className="empty-state">
        <strong>Demande indisponible</strong>
        <p>{error}</p>
        <Link className="button-secondary" href="/admin/demandes">
          Retour
        </Link>
      </div>
    );
  }

  const canDispatch =
    overview.capabilities.dispatch_requests &&
    (item.status === "CREATED" || item.status === "SEARCHING") &&
    item.offers.length === 0;

  return (
    <main>
      <section className="admin-page-head">
        <div>
          <Link className="back-link" href="/admin/demandes">
            ← Demandes
          </Link>
          <p className="page-kicker">{item.trade_name}</p>
          <h1>{item.title}</h1>
          <div className="detail-badges">
            <span className={`status-badge ${statusTone(item.status)}`}>
              {STATUS_LABELS[item.status]}
            </span>
            {item.priority === "URGENT" && (
              <span className="urgent-label">Urgente</span>
            )}
          </div>
        </div>
        {canDispatch && (
          <button
            className="button-primary"
            disabled={busy}
            type="button"
            onClick={dispatch}
          >
            {busy ? "Recherche…" : "Lancer le matching"}
          </button>
        )}
      </section>

      {message && <div className="form-success">{message}</div>}
      {error && <div className="inline-error">{error}</div>}

      <div className="detail-grid">
        <div className="detail-main">
          <section className="detail-card">
            <h2>Données de la demande</h2>
            <dl className="detail-list">
              <div><dt>Client</dt><dd>{item.client_phone}</dd></div>
              <div>
                <dt>Zone</dt>
                <dd>{item.neighborhood_name}, {item.commune_name}</dd>
              </div>
              <div><dt>Adresse</dt><dd>{item.address_detail}</dd></div>
              <div><dt>Créée le</dt><dd>{formatDate(item.created_at)}</dd></div>
            </dl>
            <div className="description-box">
              <strong>Description</strong>
              <p>{item.description}</p>
            </div>
          </section>

          <section className="detail-card">
            <h2>Historique des statuts</h2>
            <div className="timeline">
              {item.status_history.map((history, index) => (
                <div className="timeline-item" key={`${history.created_at}-${index}`}>
                  <span className="timeline-dot" />
                  <div>
                    <strong>{STATUS_LABELS[history.new_status]}</strong>
                    <small>{formatDate(history.created_at)}</small>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>

        <aside className="detail-side">
          <section className="admin-action-card">
            <p className="page-kicker">Attribution</p>
            <h2>Prestataire</h2>
            {item.assigned_provider_display_name ? (
              <p>{item.assigned_provider_display_name}</p>
            ) : (
              <p>Aucun prestataire attribué.</p>
            )}
          </section>

          <section className="detail-card">
            <h2>Offres générées</h2>
            {item.offers.length === 0 ? (
              <p className="muted-copy">Aucune offre.</p>
            ) : (
              <div className="admin-compact-list">
                {item.offers.map((offer) => (
                  <div key={offer.id}>
                    <strong>{offer.provider_display_name}</strong>
                    <span className={`status-badge ${statusTone(
                      offer.status === "ACCEPTED" ? "ACCEPTED" : "OFFERED",
                    )}`}>
                      {offer.status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="security-note">
            <strong>Données privées</strong>
            <p>
              Le téléphone, l’adresse et les textes libres n’apparaissent que
              dans cette fiche réservée aux administrateurs autorisés.
            </p>
          </section>
        </aside>
      </div>
    </main>
  );
}
