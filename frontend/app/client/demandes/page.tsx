"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import RequestCard from "@/components/client/request-card";
import {
  apiGet,
  type ApiPage,
  type ServiceRequest,
} from "@/lib/client-api";

type Filter = "ALL" | "ACTIVE" | "DONE" | "URGENT";

const FILTER_PATHS: Record<Filter, string> = {
  ALL: "/api/v1/requests/",
  ACTIVE:
    "/api/v1/requests/?status=CREATED,SEARCHING,OFFERED,ACCEPTED,EN_ROUTE,ARRIVED,IN_PROGRESS,PROVIDER_COMPLETED,DISPUTED",
  DONE: "/api/v1/requests/?status=CLIENT_CONFIRMED",
  URGENT: "/api/v1/requests/?priority=URGENT",
};

function normalizeNext(next: string | null) {
  if (!next) return null;
  const parsed = new URL(next, window.location.origin);
  return `${parsed.pathname}${parsed.search}`;
}

export default function ClientRequestsPage() {
  const [requests, setRequests] = useState<ServiceRequest[]>([]);
  const [filter, setFilter] = useState<Filter>("ALL");
  const [nextPage, setNextPage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    apiGet<ApiPage<ServiceRequest>>(FILTER_PATHS.ALL)
      .then((page) => {
        if (!active) return;
        setRequests(page.results);
        setNextPage(normalizeNext(page.next));
      })
      .catch((caught: unknown) => {
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

  async function chooseFilter(value: Filter) {
    setFilter(value);
    setLoading(true);
    setError("");
    try {
      const page = await apiGet<ApiPage<ServiceRequest>>(FILTER_PATHS[value]);
      setRequests(page.results);
      setNextPage(normalizeNext(page.next));
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Impossible de filtrer les demandes.",
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
      const page = await apiGet<ApiPage<ServiceRequest>>(nextPage);
      setRequests((current) => [...current, ...page.results]);
      setNextPage(normalizeNext(page.next));
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Impossible de charger la suite.",
      );
    } finally {
      setLoadingMore(false);
    }
  }

  return (
    <main>
      <section className="client-page-head">
        <div>
          <p className="page-kicker">Mes demandes</p>
          <h1>Historique et suivi</h1>
          <p>Retrouvez vos demandes et l’état réel communiqué par le serveur.</p>
        </div>
        <Link className="button-primary" href="/client/demandes/nouvelle">
          + Nouvelle demande
        </Link>
      </section>

      <div className="filter-row" role="group" aria-label="Filtrer les demandes">
        {[
          ["ALL", "Toutes"],
          ["ACTIVE", "Actives"],
          ["DONE", "Terminées"],
          ["URGENT", "Urgentes"],
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

      {!loading && !error && requests.length === 0 && (
        <div className="empty-state">
          <strong>Aucune demande dans cette catégorie</strong>
          <p>Changez de filtre ou créez une nouvelle demande.</p>
        </div>
      )}

      {!loading && (
        <div className="request-list">
          {requests.map((request) => (
            <RequestCard request={request} key={request.id} />
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
