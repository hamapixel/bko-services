"use client";

import { useEffect, useState } from "react";

import ProviderInterventionCard from "@/components/provider/provider-intervention-card";
import {
  apiGet,
  type ApiPage,
  type ProviderIntervention,
} from "@/lib/provider-api";

type Filter = "ACTIVE" | "WAITING" | "DONE" | "ALL";

const FILTER_PATHS: Record<Filter, string> = {
  ACTIVE:
    "/api/v1/providers/interventions/?status=ACCEPTED,EN_ROUTE,ARRIVED,IN_PROGRESS",
  WAITING: "/api/v1/providers/interventions/?status=PROVIDER_COMPLETED",
  DONE: "/api/v1/providers/interventions/?status=CLIENT_CONFIRMED",
  ALL: "/api/v1/providers/interventions/",
};

function normalizeNext(next: string | null) {
  if (!next) return null;
  const parsed = new URL(next, window.location.origin);
  return `${parsed.pathname}${parsed.search}`;
}

export default function ProviderInterventionsPage() {
  const [items, setItems] = useState<ProviderIntervention[]>([]);
  const [filter, setFilter] = useState<Filter>("ACTIVE");
  const [nextPage, setNextPage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    apiGet<ApiPage<ProviderIntervention>>(FILTER_PATHS.ACTIVE)
      .then((page) => {
        if (!active) return;
        setItems(page.results);
        setNextPage(normalizeNext(page.next));
      })
      .catch((caught) => {
        if (!active) return;
        setError(
          caught instanceof Error
            ? caught.message
            : "Impossible de charger les interventions.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  async function chooseFilter(value: Filter) {
    setFilter(value);
    setLoading(true);
    setError("");
    try {
      const page = await apiGet<ApiPage<ProviderIntervention>>(
        FILTER_PATHS[value],
      );
      setItems(page.results);
      setNextPage(normalizeNext(page.next));
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Impossible de filtrer les interventions.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function loadMore() {
    if (!nextPage) return;
    setLoadingMore(true);
    setError("");
    try {
      const page = await apiGet<ApiPage<ProviderIntervention>>(nextPage);
      setItems((current) => [...current, ...page.results]);
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
          <p className="page-kicker">Interventions</p>
          <h1>Mes missions attribuées</h1>
          <p>
            Faites avancer chaque intervention dans l’ordre imposé par le serveur.
          </p>
        </div>
      </section>

      <div className="filter-row" role="group" aria-label="Filtrer les interventions">
        {[
          ["ACTIVE", "Actives"],
          ["WAITING", "À confirmer"],
          ["DONE", "Terminées"],
          ["ALL", "Toutes"],
        ].map(([value, label]) => (
          <button
            className={filter === value ? "filter-chip active" : "filter-chip"}
            disabled={loading}
            key={value}
            type="button"
            onClick={() => chooseFilter(value as Filter)}
          >
            {label}
          </button>
        ))}
      </div>

      {loading && <div className="skeleton-list">Chargement…</div>}
      {error && <div className="inline-error">{error}</div>}

      {!loading && !error && items.length === 0 && (
        <div className="empty-state">
          <strong>Aucune intervention dans cette catégorie</strong>
          <p>Les missions acceptées apparaîtront ici.</p>
        </div>
      )}

      {!loading && (
        <div className="request-list">
          {items.map((item) => (
            <ProviderInterventionCard intervention={item} key={item.id} />
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
