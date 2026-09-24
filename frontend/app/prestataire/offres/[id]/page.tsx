"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  apiGet,
  apiMutation,
  formatDate,
  type ProviderOffer,
} from "@/lib/provider-api";

type AcceptResponse = {
  id: string;
  request_id: string;
  status: string;
  request_status: string;
  assigned_provider_id: string;
};

export default function ProviderOfferDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [offer, setOffer] = useState<ProviderOffer | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    apiGet<ProviderOffer>(`/api/v1/providers/offers/${params.id}/`)
      .then((data) => {
        if (active) setOffer(data);
      })
      .catch((caught) => {
        if (!active) return;
        setError(
          caught instanceof Error ? caught.message : "Offre introuvable.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [params.id]);

  async function acceptOffer() {
    if (
      !window.confirm(
        "Accepter cette mission ? L’attribution sera décidée atomiquement par le serveur.",
      )
    ) {
      return;
    }

    setBusy(true);
    setError("");
    try {
      const accepted = await apiMutation<AcceptResponse>(
        `/api/v1/providers/offers/${params.id}/accept/`,
        "POST",
        {},
      );
      router.replace(`/prestataire/interventions/${accepted.request_id}`);
      router.refresh();
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Cette offre ne peut plus être acceptée.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return <div className="skeleton-list">Chargement de l’offre…</div>;
  }

  if (error && !offer) {
    return (
      <div className="empty-state">
        <strong>Offre indisponible</strong>
        <p>{error}</p>
        <Link className="button-secondary" href="/prestataire/offres">
          Retour aux offres
        </Link>
      </div>
    );
  }

  if (!offer) return null;

  return (
    <main>
      <section className="provider-page-head">
        <div>
          <Link className="back-link" href="/prestataire/offres">
            ← Offres
          </Link>
          <p className="page-kicker">{offer.trade_name}</p>
          <h1>{offer.title}</h1>
          <div className="detail-badges">
            <span className="status-badge neutral">Offre en attente</span>
            {offer.priority === "URGENT" && (
              <span className="urgent-label">Urgente</span>
            )}
          </div>
        </div>
      </section>

      {error && <div className="inline-error">{error}</div>}

      <div className="detail-grid">
        <section className="detail-card">
          <h2>Mission proposée</h2>
          <dl className="detail-list">
            <div>
              <dt>Métier</dt>
              <dd>{offer.trade_name}</dd>
            </div>
            <div>
              <dt>Zone</dt>
              <dd>{offer.neighborhood_name}, {offer.commune_name}</dd>
            </div>
            <div>
              <dt>Priorité</dt>
              <dd>{offer.priority === "URGENT" ? "Urgente" : "Normale"}</dd>
            </div>
            <div>
              <dt>Reçue le</dt>
              <dd>{formatDate(offer.created_at)}</dd>
            </div>
          </dl>
          <div className="description-box">
            <strong>Description</strong>
            <p>{offer.description}</p>
          </div>
        </section>

        <aside className="detail-side">
          <section className="provider-accept-card">
            <p className="page-kicker">Attribution sécurisée</p>
            <h2>Accepter cette mission</h2>
            <p>
              Le serveur revérifie votre disponibilité, votre abonnement et
              l’état de l’offre au moment exact de l’acceptation.
            </p>
            <button
              className="button-primary button-wide"
              disabled={busy}
              type="button"
              onClick={acceptOffer}
            >
              {busy ? "Vérification…" : "Accepter la mission"}
            </button>
          </section>
          <section className="security-note">
            <strong>Données privées masquées</strong>
            <p>
              L’adresse précise et le téléphone apparaîtront uniquement si
              l’attribution vous est réellement accordée.
            </p>
          </section>
        </aside>
      </div>
    </main>
  );
}
