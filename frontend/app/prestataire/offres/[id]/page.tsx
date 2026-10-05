"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useBkoAlert } from "@/components/bko-alert";
import { ApiReadError } from "@/lib/client-api";
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
  const alerts = useBkoAlert();
  const [offer, setOffer] = useState<ProviderOffer | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    let fetching = false;
    async function refresh() {
      if (!active || fetching || document.visibilityState === "hidden") return;
      fetching = true;
      try {
        const data = await apiGet<ProviderOffer>(`/api/v1/providers/offers/${params.id}/`);
        if (active) {
          setOffer(data);
          setError("");
        }
      } catch (caught) {
        if (!active) return;
        if (caught instanceof ApiReadError && caught.status === 404) {
          setOffer(null);
          setError("Cette offre n’est plus disponible : la mission a pu être attribuée à un autre prestataire.");
        } else {
          setError(caught instanceof Error ? caught.message : "Offre introuvable.");
        }
      } finally {
        fetching = false;
        if (active) setLoading(false);
      }
    }
    function onVisibilityChange() {
      if (document.visibilityState === "visible") void refresh();
    }
    void refresh();
    const interval = window.setInterval(() => void refresh(), 20_000);
    window.addEventListener("focus", onVisibilityChange);
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      active = false;
      window.clearInterval(interval);
      window.removeEventListener("focus", onVisibilityChange);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [params.id]);

  async function acceptOffer() {
    const confirmed = await alerts.confirmAction({
      title: "Accepter cette mission ?",
      message:
        "Le serveur revérifiera votre disponibilité, votre abonnement et l’état exact de l’offre. Une seule acceptation peut gagner.",
      confirmLabel: "Accepter la mission",
    });
    if (!confirmed) return;

    setBusy(true);
    setError("");
    try {
      const accepted = await apiMutation<AcceptResponse>(
        `/api/v1/providers/offers/${params.id}/accept/`,
        "POST",
        {},
      );
      alerts.success({
        title: "Mission attribuée",
        message: "Le serveur a confirmé que cette intervention vous est attribuée.",
      });
      router.replace(`/prestataire/interventions/${accepted.request_id}`);
      router.refresh();
    } catch (caught) {
      const message =
        caught instanceof Error
          ? caught.message
          : "Cette offre ne peut plus être acceptée.";
      setError(message);
      alerts.error({ title: "Acceptation refusée", message });
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
          <h1>{offer.trade_name} · {offer.neighborhood_name}</h1>
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
          <div className="provider-offer-privacy">
            Le titre, la description libre, l’adresse précise et le téléphone
            du client restent masqués avant attribution, car ces champs peuvent
            contenir des informations personnelles.
          </div>
          {offer.outside_declared_quartiers && (
            <p className="provider-offer-zone-note">Cette mission est dans un autre quartier de la même commune. Vérifiez que vous pouvez vous y déplacer avant d’accepter.</p>
          )}
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
              Le titre, la description, l’adresse précise et le téléphone du client
              apparaîtront uniquement si l’attribution vous est réellement accordée.
            </p>
          </section>
        </aside>
      </div>
    </main>
  );
}
