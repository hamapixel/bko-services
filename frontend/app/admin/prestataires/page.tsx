"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  ADMIN_PROVIDER_STATUS_LABELS,
  adminStatusTone,
  apiGet,
  formatDate,
  type AdminProvider,
  type ApiPage,
} from "@/lib/admin-api";

type Filter = "ALL" | AdminProvider["status"];

const FILTERS: Array<[Filter, string]> = [
  ["ALL", "Tous"],
  ["PENDING", "En attente"],
  ["VERIFIED", "Vérifiés"],
  ["REJECTED", "Refusés"],
  ["SUSPENDED", "Suspendus"],
];

function normalizeNext(next: string | null) {
  if (!next) return null;
  const parsed = new URL(next, window.location.origin);
  return `${parsed.pathname}${parsed.search}`;
}

export default function AdminProvidersPage() {
  const [items, setItems] = useState<AdminProvider[]>([]);
  const [filter, setFilter] = useState<Filter>("PENDING");
  const [query, setQuery] = useState("");
  const [nextPage, setNextPage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");

  async function load(value: Filter, search = query) {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      if (value !== "ALL") params.set("status", value);
      if (search.trim()) params.set("q", search.trim());
      const suffix = params.toString() ? `?${params.toString()}` : "";
      const page = await apiGet<ApiPage<AdminProvider>>(
        `/api/v1/admin/providers/${suffix}`,
      );
      setItems(page.results);
      setNextPage(normalizeNext(page.next));
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Impossible de charger les prestataires.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let active = true;
    apiGet<ApiPage<AdminProvider>>("/api/v1/admin/providers/?status=PENDING")
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
            : "Impossible de charger les prestataires.",
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
    try {
      const page = await apiGet<ApiPage<AdminProvider>>(nextPage);
      setItems((current) => [...current, ...page.results]);
      setNextPage(normalizeNext(page.next));
    } finally {
      setLoadingMore(false);
    }
  }

  return (
    <main>
      <section className="admin-page-head">
        <div>
          <p className="page-kicker">Prestataires</p>
          <h1>Validation et supervision</h1>
          <p>
            Les décisions changent le rôle du compte uniquement via le service
            backend audité.
          </p>
        </div>
      </section>

      <form
        className="admin-search-row"
        onSubmit={(event) => {
          event.preventDefault();
          void load(filter, query);
        }}
      >
        <input
          aria-label="Rechercher un prestataire"
          placeholder="Nom, raison sociale ou téléphone"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <button className="button-secondary" type="submit">
          Rechercher
        </button>
      </form>

      <div className="filter-row">
        {FILTERS.map(([value, label]) => (
          <button
            className={filter === value ? "filter-chip active" : "filter-chip"}
            key={value}
            type="button"
            onClick={() => {
              setFilter(value);
              void load(value, query);
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {loading && <div className="skeleton-list">Chargement…</div>}
      {error && <div className="inline-error">{error}</div>}

      {!loading && !error && items.length === 0 && (
        <div className="empty-state">
          <strong>Aucun dossier</strong>
          <p>Aucun prestataire ne correspond à ce filtre.</p>
        </div>
      )}

      <div className="admin-list">
        {items.map((provider) => (
          <Link
            className="admin-list-card"
            href={`/admin/prestataires/${provider.id}`}
            key={provider.id}
          >
            <div>
              <span className="request-meta">
                {provider.trade_details.map((trade) => trade.name).slice(0, 2).join(" · ") || "Aucun métier"}
              </span>
              <h3>{provider.display_name}</h3>
              <p>{provider.legal_name}</p>
            </div>
            <div className="admin-list-meta">
              <span className={`status-badge ${adminStatusTone(provider.status)}`}>
                {ADMIN_PROVIDER_STATUS_LABELS[provider.status]}
              </span>
              <small>{provider.user_phone}</small>
              <small>{formatDate(provider.created_at)}</small>
            </div>
          </Link>
        ))}
      </div>

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
