"use client";

import { useEffect, useState } from "react";

import ProviderOfferCard from "@/components/provider/provider-offer-card";
import { apiGetAll } from "@/lib/client-api";
import type { ProviderOffer } from "@/lib/provider-api";

export default function ProviderOffersPage() {
  const [offers, setOffers] = useState<ProviderOffer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    let fetching = false;
    async function refresh(initial = false) {
      if (!active || fetching || document.visibilityState === "hidden") return;
      fetching = true;
      try {
        const items = await apiGetAll<ProviderOffer>("/api/v1/providers/offers/");
        if (active) {
          setOffers(items);
          setError("");
        }
      } catch (caught) {
        if (active && initial) setError(
          caught instanceof Error ? caught.message : "Impossible de charger les offres.",
        );
      } finally {
        fetching = false;
        if (active) setLoading(false);
      }
    }
    function onVisibilityChange() {
      if (document.visibilityState === "visible") void refresh();
    }
    void refresh(true);
    const interval = window.setInterval(() => void refresh(), 20_000);
    window.addEventListener("focus", onVisibilityChange);
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      active = false;
      window.clearInterval(interval);
      window.removeEventListener("focus", onVisibilityChange);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, []);

  return (
    <main>
      <section className="provider-page-head">
        <div>
          <p className="page-kicker">Offres</p>
          <h1>Nouvelles missions</h1>
          <p>
            Ces offres correspondent à votre métier, à vos quartiers ou à leur commune,
            à votre disponibilité et à votre abonnement.
          </p>
        </div>
      </section>

      <div className="provider-privacy-callout">
        <strong>Confidentialité avant attribution</strong>
        <p>
          Vous voyez le besoin et la zone générale. L’adresse précise et le
          téléphone du client restent masqués jusqu’à votre acceptation réussie.
        </p>
      </div>

      {loading && <div className="skeleton-list">Chargement des offres…</div>}
      {error && <div className="inline-error">{error}</div>}

      {!loading && !error && offers.length === 0 && (
        <div className="empty-state">
          <strong>Aucune offre disponible</strong>
          <p>Revenez plus tard ou vérifiez votre disponibilité et votre abonnement.</p>
        </div>
      )}

      {!loading && (
        <div className="provider-offer-grid">
          {offers.map((offer) => (
            <ProviderOfferCard offer={offer} key={offer.id} />
          ))}
        </div>
      )}

    </main>
  );
}
