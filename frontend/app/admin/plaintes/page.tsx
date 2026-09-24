"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  COMPLAINT_CATEGORY_LABELS,
  COMPLAINT_STATUS_LABELS,
  adminStatusTone,
  apiGet,
  formatDate,
  type AdminComplaint,
  type ApiPage,
} from "@/lib/admin-api";

type Filter = "ACTIVE" | AdminComplaint["status"] | "ALL";

const FILTERS: Array<[Filter, string]> = [
  ["ACTIVE", "Actives"],
  ["OPEN", "Ouvertes"],
  ["UNDER_REVIEW", "En examen"],
  ["RESOLVED", "Résolues"],
  ["REJECTED", "Rejetées"],
  ["ALL", "Toutes"],
];

function pathFor(filter: Filter) {
  if (filter === "ALL") return "/api/v1/complaints/admin/";
  if (filter === "ACTIVE") {
    return "/api/v1/complaints/admin/?status=OPEN,UNDER_REVIEW";
  }
  return `/api/v1/complaints/admin/?status=${filter}`;
}

function normalizeNext(next: string | null) {
  if (!next) return null;
  const parsed = new URL(next, window.location.origin);
  return `${parsed.pathname}${parsed.search}`;
}

export default function AdminComplaintsPage() {
  const [items, setItems] = useState<AdminComplaint[]>([]);
  const [filter, setFilter] = useState<Filter>("ACTIVE");
  const [nextPage, setNextPage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");

  async function load(value: Filter) {
    setLoading(true);
    setError("");
    try {
      const page = await apiGet<ApiPage<AdminComplaint>>(pathFor(value));
      setItems(page.results);
      setNextPage(normalizeNext(page.next));
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Impossible de charger les plaintes.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let active = true;
    apiGet<ApiPage<AdminComplaint>>(pathFor("ACTIVE"))
      .then((page) => {
        if (!active) return;
        setItems(page.results);
        setNextPage(normalizeNext(page.next));
      })
      .catch((caught) => {
        if (!active) return;
        setError(
          caught instanceof Error ? caught.message : "Impossible de charger les plaintes.",
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
      const page = await apiGet<ApiPage<AdminComplaint>>(nextPage);
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
          <p className="page-kicker">Plaintes</p>
          <h1>Signalements et litiges</h1>
          <p>
            Une plainte active place l’intervention en état contesté jusqu’à la
            décision administrative finale.
          </p>
        </div>
      </section>

      <div className="filter-row">
        {FILTERS.map(([value, label]) => (
          <button
            className={filter === value ? "filter-chip active" : "filter-chip"}
            key={value}
            type="button"
            onClick={() => {
              setFilter(value);
              void load(value);
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
          <strong>Aucune plainte</strong>
          <p>Aucun signalement ne correspond à ce filtre.</p>
        </div>
      )}

      <div className="admin-list">
        {items.map((item) => (
          <Link
            className="admin-list-card"
            href={`/admin/plaintes/${item.id}`}
            key={item.id}
          >
            <div>
              <span className="request-meta">
                {COMPLAINT_CATEGORY_LABELS[item.category]}
              </span>
              <h3>Intervention {item.service_request_id.slice(0, 8)}…</h3>
              <p>
                Signalé par {item.reporter_role} · {item.reporter_id.slice(0, 8)}…
              </p>
            </div>
            <div className="admin-list-meta">
              <span className={`status-badge ${adminStatusTone(item.status)}`}>
                {COMPLAINT_STATUS_LABELS[item.status]}
              </span>
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
