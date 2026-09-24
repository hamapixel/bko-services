"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  apiGet,
  formatDate,
  type AdminRequestRow,
  type ApiPage,
} from "@/lib/admin-api";
import { STATUS_LABELS, statusTone } from "@/lib/client-api";

type Filter = "ALL" | "ACTIVE" | "CREATED" | "DISPUTED" | "DONE";

const FILTER_PATHS: Record<Filter, string> = {
  ALL: "/api/v1/admin/requests/",
  ACTIVE:
    "/api/v1/admin/requests/?status=CREATED,SEARCHING,OFFERED,ACCEPTED,EN_ROUTE,ARRIVED,IN_PROGRESS,PROVIDER_COMPLETED,DISPUTED",
  CREATED: "/api/v1/admin/requests/?status=CREATED,SEARCHING",
  DISPUTED: "/api/v1/admin/requests/?status=DISPUTED",
  DONE: "/api/v1/admin/requests/?status=CLIENT_CONFIRMED,CANCELLED",
};

function normalizeNext(next: string | null) {
  if (!next) return null;
  const parsed = new URL(next, window.location.origin);
  return `${parsed.pathname}${parsed.search}`;
}

export default function AdminRequestsPage() {
  const [items, setItems] = useState<AdminRequestRow[]>([]);
  const [filter, setFilter] = useState<Filter>("ACTIVE");
  const [priority, setPriority] = useState<"" | "NORMAL" | "URGENT">("");
  const [nextPage, setNextPage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");

  async function load(value: Filter, selectedPriority = priority) {
    setLoading(true);
    setError("");
    try {
      const base = FILTER_PATHS[value];
      const join = base.includes("?") ? "&" : "?";
      const path = selectedPriority
        ? `${base}${join}priority=${selectedPriority}`
        : base;
      const page = await apiGet<ApiPage<AdminRequestRow>>(path);
      setItems(page.results);
      setNextPage(normalizeNext(page.next));
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Impossible de charger les demandes.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let active = true;
    apiGet<ApiPage<AdminRequestRow>>(FILTER_PATHS.ACTIVE)
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
            : "Impossible de charger les demandes.",
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
      const page = await apiGet<ApiPage<AdminRequestRow>>(nextPage);
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
          <p className="page-kicker">Demandes</p>
          <h1>Supervision des interventions</h1>
          <p>
            La liste masque les textes libres et coordonnées. Les détails privés
            sont réservés à la fiche d’une demande.
          </p>
        </div>
      </section>

      <div className="admin-filter-bar">
        <div className="filter-row">
          {[
            ["ACTIVE", "Actives"],
            ["CREATED", "À matcher"],
            ["DISPUTED", "Contestées"],
            ["DONE", "Terminées"],
            ["ALL", "Toutes"],
          ].map(([value, label]) => (
            <button
              className={filter === value ? "filter-chip active" : "filter-chip"}
              key={value}
              type="button"
              onClick={() => {
                const next = value as Filter;
                setFilter(next);
                void load(next, priority);
              }}
            >
              {label}
            </button>
          ))}
        </div>

        <select
          aria-label="Filtrer par priorité"
          value={priority}
          onChange={(event) => {
            const next = event.target.value as "" | "NORMAL" | "URGENT";
            setPriority(next);
            void load(filter, next);
          }}
        >
          <option value="">Toutes priorités</option>
          <option value="NORMAL">Normales</option>
          <option value="URGENT">Urgentes</option>
        </select>
      </div>

      {loading && <div className="skeleton-list">Chargement…</div>}
      {error && <div className="inline-error">{error}</div>}

      {!loading && !error && items.length === 0 && (
        <div className="empty-state">
          <strong>Aucune demande</strong>
          <p>Aucune demande ne correspond à ce filtre.</p>
        </div>
      )}

      <div className="admin-list">
        {items.map((item) => (
          <Link
            className="admin-list-card"
            href={`/admin/demandes/${item.id}`}
            key={item.id}
          >
            <div>
              <span className="request-meta">
                {item.trade_name} · {item.commune_name}
              </span>
              <h3>{item.neighborhood_name}</h3>
              <p>
                Client {item.client_id.slice(0, 8)}…
                {item.assigned_provider_display_name
                  ? ` · ${item.assigned_provider_display_name}`
                  : " · non attribuée"}
              </p>
            </div>
            <div className="admin-list-meta">
              <span className={`status-badge ${statusTone(item.status)}`}>
                {STATUS_LABELS[item.status]}
              </span>
              {item.priority === "URGENT" && (
                <span className="urgent-label">Urgente</span>
              )}
              <small>{formatDate(item.created_at)}</small>
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
