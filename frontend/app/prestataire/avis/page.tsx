"use client";

import { useEffect, useMemo, useState } from "react";

import { useProviderSession } from "@/components/provider/provider-shell";
import {
  apiGet,
  formatDate,
  type ApiPage,
  type PublicReview,
} from "@/lib/provider-api";

function normalizeNext(next: string | null) {
  if (!next) return null;
  const parsed = new URL(next, window.location.origin);
  return `${parsed.pathname}${parsed.search}`;
}

export default function ProviderReviewsPage() {
  const { profile } = useProviderSession();
  const [reviews, setReviews] = useState<PublicReview[]>([]);
  const [nextPage, setNextPage] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    apiGet<ApiPage<PublicReview>>(
      `/api/v1/providers/${profile.id}/reviews/`,
    )
      .then((page) => {
        if (!active) return;
        setReviews(page.results);
        setTotal(page.count);
        setNextPage(normalizeNext(page.next));
      })
      .catch((caught) => {
        if (!active) return;
        setError(
          caught instanceof Error ? caught.message : "Impossible de charger les avis.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [profile.id]);

  const average = useMemo(() => {
    if (!reviews.length) return null;
    return reviews.reduce((sum, review) => sum + review.rating, 0) / reviews.length;
  }, [reviews]);

  async function loadMore() {
    if (!nextPage) return;
    setLoadingMore(true);
    setError("");
    try {
      const page = await apiGet<ApiPage<PublicReview>>(nextPage);
      setReviews((current) => [...current, ...page.results]);
      setNextPage(normalizeNext(page.next));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Chargement impossible.");
    } finally {
      setLoadingMore(false);
    }
  }

  return (
    <main>
      <section className="provider-page-head">
        <div>
          <p className="page-kicker">Réputation</p>
          <h1>Mes avis clients</h1>
          <p>
            Les avis apparaissent uniquement après confirmation complète d’une
            intervention par le client.
          </p>
        </div>
      </section>

      <section className="provider-review-summary">
        <div>
          <span>Avis publiés</span>
          <strong>{total}</strong>
        </div>
        <div>
          <span>Moyenne affichée</span>
          <strong>{average === null ? "—" : `${average.toFixed(1)} / 5`}</strong>
          <small>Calculée sur les avis actuellement chargés</small>
        </div>
      </section>

      {loading && <div className="skeleton-list">Chargement des avis…</div>}
      {error && <div className="inline-error">{error}</div>}

      {!loading && !error && reviews.length === 0 && (
        <div className="empty-state">
          <strong>Aucun avis pour le moment</strong>
          <p>Les futurs avis clients apparaîtront ici.</p>
        </div>
      )}

      <div className="provider-review-list">
        {reviews.map((review) => (
          <article className="provider-review-card" key={review.id}>
            <div className="provider-stars" aria-label={`${review.rating} sur 5`}>
              {"★".repeat(review.rating)}
              <span>{"★".repeat(5 - review.rating)}</span>
            </div>
            <p>{review.comment || "Aucun commentaire."}</p>
            <small>{formatDate(review.created_at)}</small>
          </article>
        ))}
      </div>

      {nextPage && (
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
