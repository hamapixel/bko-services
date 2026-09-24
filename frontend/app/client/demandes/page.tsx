"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import RequestCard from "@/components/client/request-card";
import {
  apiGet,
  type ApiPage,
  type RequestStatus,
  type ServiceRequest,
} from "@/lib/client-api";

type Filter = "ALL" | "ACTIVE" | "DONE" | "URGENT";

export default function ClientRequestsPage() {
  const [requests, setRequests] = useState<ServiceRequest[]>([]);
  const [filter, setFilter] = useState<Filter>("ALL");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    apiGet<ApiPage<ServiceRequest>>("/api/v1/requests/")
      .then((page) => {
        if (active) setRequests(page.results);
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

  const visible = useMemo(() => {
    const terminal: RequestStatus[] = ["CLIENT_CONFIRMED", "CANCELLED"];
    if (filter === "ACTIVE") {
      return requests.filter((request) => !terminal.includes(request.status));
    }
    if (filter === "DONE") {
      return requests.filter((request) => request.status === "CLIENT_CONFIRMED");
    }
    if (filter === "URGENT") {
      return requests.filter((request) => request.priority === "URGENT");
    }
    return requests;
  }, [filter, requests]);

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
            key={value}
            type="button"
            onClick={() => setFilter(value as Filter)}
          >
            {label}
          </button>
        ))}
      </div>

      {loading && <div className="skeleton-list">Chargement…</div>}
      {error && <div className="inline-error">{error}</div>}

      {!loading && !error && visible.length === 0 && (
        <div className="empty-state">
          <strong>Aucune demande dans cette catégorie</strong>
          <p>Changez de filtre ou créez une nouvelle demande.</p>
        </div>
      )}

      <div className="request-list">
        {visible.map((request) => (
          <RequestCard request={request} key={request.id} />
        ))}
      </div>
    </main>
  );
}
