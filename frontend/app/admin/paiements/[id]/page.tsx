"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { useAdminSession } from "@/components/admin/admin-shell";
import {
  adminStatusTone,
  apiGet,
  apiMutation,
  formatDate,
  type AdminPayment,
} from "@/lib/admin-api";
import { PAYMENT_STATUS_LABELS, formatXof } from "@/lib/provider-api";

export default function AdminPaymentDetailPage() {
  const params = useParams<{ id: string }>();
  const { refreshOverview } = useAdminSession();
  const [payment, setPayment] = useState<AdminPayment | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    let active = true;
    apiGet<AdminPayment>(
      `/api/v1/payments/admin/transactions/${params.id}/`,
    )
      .then((data) => {
        if (active) setPayment(data);
      })
      .catch((caught) => {
        if (!active) return;
        setError(
          caught instanceof Error ? caught.message : "Transaction introuvable.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [params.id]);

  async function retryFulfillment() {
    if (!payment) return;
    if (
      !window.confirm(
        "Retenter uniquement l’application de l’abonnement pour ce paiement déjà confirmé ?",
      )
    ) {
      return;
    }

    setBusy(true);
    setError("");
    setMessage("");
    try {
      const updated = await apiMutation<AdminPayment>(
        `/api/v1/payments/admin/transactions/${payment.id}/retry-fulfillment/`,
        "POST",
        {},
      );
      setPayment(updated);
      setMessage(
        updated.fulfilled_at
          ? "Abonnement appliqué avec succès."
          : "Le retraitement reste en échec ; consultez le code d’erreur.",
      );
      await refreshOverview();
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Retraitement impossible.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <div className="skeleton-list">Chargement…</div>;
  if (!payment) {
    return (
      <div className="empty-state">
        <strong>Transaction indisponible</strong>
        <p>{error}</p>
        <Link className="button-secondary" href="/admin/paiements">Retour</Link>
      </div>
    );
  }

  const retryable =
    payment.status === "SUCCEEDED" && payment.fulfilled_at === null;

  return (
    <main>
      <section className="admin-page-head">
        <div>
          <Link className="back-link" href="/admin/paiements">← Paiements</Link>
          <p className="page-kicker">{payment.plan_name_snapshot}</p>
          <h1>{payment.merchant_reference}</h1>
          <span className={`status-badge ${adminStatusTone(payment.status)}`}>
            {PAYMENT_STATUS_LABELS[payment.status]}
          </span>
        </div>
        {retryable && (
          <button
            className="button-primary"
            disabled={busy}
            type="button"
            onClick={retryFulfillment}
          >
            {busy ? "Retraitement…" : "Retenter l’application"}
          </button>
        )}
      </section>

      {message && <div className="form-success">{message}</div>}
      {error && <div className="inline-error">{error}</div>}

      <div className="detail-grid">
        <div className="detail-main">
          <section className="detail-card">
            <h2>Transaction</h2>
            <dl className="detail-list">
              <div><dt>Prestataire</dt><dd>{payment.provider_display_name}</dd></div>
              <div><dt>Montant</dt><dd>{formatXof(payment.amount_xof)}</dd></div>
              <div><dt>Objet</dt><dd>{payment.purpose}</dd></div>
              <div><dt>Durée figée</dt><dd>{payment.duration_days_snapshot} jours</dd></div>
              <div><dt>Créée le</dt><dd>{formatDate(payment.created_at)}</dd></div>
              <div>
                <dt>Confirmée le</dt>
                <dd>{payment.confirmed_at ? formatDate(payment.confirmed_at) : "—"}</dd>
              </div>
              <div>
                <dt>Appliquée le</dt>
                <dd>{payment.fulfilled_at ? formatDate(payment.fulfilled_at) : "—"}</dd>
              </div>
              <div>
                <dt>Référence fournisseur</dt>
                <dd>{payment.provider_transaction_id || "—"}</dd>
              </div>
            </dl>
          </section>

          {payment.fulfillment_error_code && (
            <section className="inline-error">
              <strong>Erreur d’application</strong>
              <p>{payment.fulfillment_error_code}</p>
            </section>
          )}
        </div>

        <aside className="detail-side">
          <section className="security-note">
            <strong>Statut financier immuable côté UI</strong>
            <p>
              Aucun bouton de cette interface ne transforme un paiement en
              SUCCEEDED. Le retraitement ne concerne que l’abonnement après un
              paiement déjà confirmé.
            </p>
          </section>
        </aside>
      </div>
    </main>
  );
}
