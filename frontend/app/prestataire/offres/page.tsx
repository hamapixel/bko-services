"use client";

import { useEffect, useState } from "react";

import ProviderOfferCard from "@/components/provider/provider-offer-card";
import {
  apiGet,
  type ApiPage,
  type ProviderOffer,
} from "@/lib/provider-api";

function normalizeNext(next: string | null) {
  if (!next) return null;
  const parsed = new URL(next, window.location.origin);
  return `${parsed.pathname}${parsed.search}`;
}

export default function ProviderOffersPage() {
  const [offers, setOffers] = useState<ProviderOffer[]>([]);
  const [nextPage, setNextPage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    apiGet<ApiPage<ProviderOffer>>("/api/v1/providers/offers/")
      .then((page) => {
        if (!active) return;
        setOffers(page.results);
        setNextPage(normalizeNext(page.next));
      })
      .catch((caught) => {
        if (!active) return;
        setError(
          caught instanceof Error
            ? caught.message
            : "Impossible de charger les offres.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  async function loadMore() {
    if (!nextPage) return;
    setLoadingMore(true);
    setError("");
    try {
      const page = await apiGet<ApiPage<ProviderOffer>>(nextPage);
      setOffers((current) => [...current, ...page.results]);
      setNextPage(normalizeNext(page.next));
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Chargement impossible.",
      );
    } finally {
      setLoadingMore(false);
    }
  }

  return (
    <main>
      <section className="provider-page-head">
        <div>
          <p className="page-kicker">Offres</p>
          <h1>Nouvelles missions</h1>
          <p>
            Ces offres sont filtrées côté serveur selon votre métier, votre zone,
            votre disponibilité et votre abonnement.
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

      {nextPage && !loading && (
        <div className="load-more-row">
          <button
            className="button-secondary"
            disabled={loadingMore}
            type="button"
            onClick={loadMore}
          >
            {loadingMore ? "Chargement…" : "Charger plus"}
          </button>
        </div>
      )}
    </main>
  );
}
