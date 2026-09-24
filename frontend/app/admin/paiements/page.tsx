"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  adminStatusTone,
  apiGet,
  formatDate,
  type AdminPayment,
  type ApiPage,
} from "@/lib/admin-api";
import { PAYMENT_STATUS_LABELS, formatXof } from "@/lib/provider-api";

type Filter = "ALL" | AdminPayment["status"];

function pathFor(filter: Filter) {
  return filter === "ALL"
    ? "/api/v1/payments/admin/transactions/"
    : `/api/v1/payments/admin/transactions/?status=${filter}`;
}

function normalizeNext(next: string | null) {
  if (!next) return null;
  const parsed = new URL(next, window.location.origin);
  return `${parsed.pathname}${parsed.search}`;
}

export default function AdminPaymentsPage() {
  const [items, setItems] = useState<AdminPayment[]>([]);
  const [filter, setFilter] = useState<Filter>("PENDING");
  const [nextPage, setNextPage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");

  async function load(value: Filter) {
    setLoading(true);
    setError("");
    try {
      const page = await apiGet<ApiPage<AdminPayment>>(pathFor(value));
      setItems(page.results);
      setNextPage(normalizeNext(page.next));
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Impossible de charger les paiements.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let active = true;
    apiGet<ApiPage<AdminPayment>>(pathFor("PENDING"))
      .then((page) => {
        if (!active) return;
        setItems(page.results);
        setNextPage(normalizeNext(page.next));
      })
      .catch((caught) => {
        if (!active) return;
        setError(
          caught instanceof Error ? caught.message : "Impossible de charger les paiements.",
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
      const page = await apiGet<ApiPage<AdminPayment>>(nextPage);
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
          <p className="page-kicker">Paiements</p>
          <h1>Audit des transactions</h1>
          <p>
            L’interface ne peut jamais confirmer un paiement. Le statut réussi
            provient uniquement du webhook signé.
          </p>
        </div>
      </section>

      <div className="filter-row">
        {[
          ["PENDING", "En attente"],
          ["SUCCEEDED", "Réussis"],
          ["FAILED", "Échoués"],
          ["CANCELLED", "Annulés"],
          ["ALL", "Tous"],
        ].map(([value, label]) => (
          <button
            className={filter === value ? "filter-chip active" : "filter-chip"}
            key={value}
            type="button"
            onClick={() => {
              const next = value as Filter;
              setFilter(next);
              void load(next);
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
          <strong>Aucune transaction</strong>
          <p>Aucune transaction ne correspond à ce filtre.</p>
        </div>
      )}

      <div className="admin-list">
        {items.map((item) => (
          <Link
            className="admin-list-card"
            href={`/admin/paiements/${item.id}`}
            key={item.id}
          >
            <div>
              <span className="request-meta">{item.plan_name_snapshot}</span>
              <h3>{item.merchant_reference}</h3>
              <p>{item.provider_display_name}</p>
            </div>
            <div className="admin-list-meta">
              <strong>{formatXof(item.amount_xof)}</strong>
              <span className={`status-badge ${adminStatusTone(item.status)}`}>
                {PAYMENT_STATUS_LABELS[item.status]}
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
