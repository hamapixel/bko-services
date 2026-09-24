"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import RequestCard from "@/components/client/request-card";
import { useClientSession } from "@/components/client/client-shell";
import {
  apiGet,
  type ApiPage,
  type ServiceRequest,
} from "@/lib/client-api";
import { listRequestDrafts } from "@/lib/offline-drafts";

export default function ClientDashboardPage() {
  const { user } = useClientSession();
  const [requests, setRequests] = useState<ServiceRequest[]>([]);
  const [draftCount, setDraftCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    Promise.all([
      apiGet<ApiPage<ServiceRequest>>("/api/v1/requests/"),
      listRequestDrafts().catch(() => []),
    ])
      .then(([requestPage, drafts]) => {
        if (!active) return;
        setRequests(requestPage.results);
        setDraftCount(drafts.length);
      })
      .catch((caught: unknown) => {
        if (!active) return;
        setError(
          caught instanceof Error
            ? caught.message
            : "Impossible de charger le tableau de bord.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const activeRequests = requests.filter(
    (request) =>
      !["CLIENT_CONFIRMED", "CANCELLED"].includes(request.status),
  );
  const completed = requests.filter(
    (request) => request.status === "CLIENT_CONFIRMED",
  );
  const waitingConfirmation = requests.filter(
    (request) => request.status === "PROVIDER_COMPLETED",
  );

  return (
    <main>
      <section className="client-page-head dashboard-head">
        <div>
          <p className="page-kicker">Bonjour</p>
          <h1>
            {user.first_name ? `${user.first_name},` : "Bienvenue,"} que
            souhaitez-vous faire ?
          </h1>
          <p>
            Créez une demande et suivez chaque étape jusqu’à la fin de
            l’intervention.
          </p>
        </div>
        <Link className="button-primary" href="/client/demandes/nouvelle">
          + Nouvelle demande
        </Link>
      </section>

      {!user.phone_verified_at && (
        <section className="dashboard-callout warning-card">
          <div>
            <strong>Vérifiez votre numéro avant votre première demande.</strong>
            <p>
              Cette vérification protège votre compte et permet au prestataire
              attribué de vous contacter.
            </p>
          </div>
          <Link className="button-secondary" href="/client/profil">
            Vérifier mon numéro
          </Link>
        </section>
      )}

      <section className="metric-grid" aria-label="Résumé">
        <article className="metric-card">
          <span>Demandes actives</span>
          <strong>{activeRequests.length}</strong>
          <small>En cours ou en recherche</small>
        </article>
        <article className="metric-card">
          <span>À confirmer</span>
          <strong>{waitingConfirmation.length}</strong>
          <small>Terminées par le prestataire</small>
        </article>
        <article className="metric-card">
          <span>Terminées</span>
          <strong>{completed.length}</strong>
          <small>Confirmées par vous</small>
        </article>
        <article className="metric-card">
          <span>Brouillons</span>
          <strong>{draftCount}</strong>
          <small>Stockés seulement sur cet appareil</small>
        </article>
      </section>

      <section className="content-section">
        <div className="section-heading">
          <div>
            <p className="page-kicker">Suivi</p>
            <h2>Demandes récentes</h2>
          </div>
          <Link className="text-link" href="/client/demandes">
            Voir tout
          </Link>
        </div>

        {loading && <div className="skeleton-list">Chargement des demandes…</div>}

        {error && (
          <div className="inline-error" role="alert">
            {error}
          </div>
        )}

        {!loading && !error && requests.length === 0 && (
          <div className="empty-state compact">
            <strong>Aucune demande pour le moment</strong>
            <p>
              Décrivez votre besoin et BKO Services enregistrera votre première
              demande.
            </p>
            <Link className="button-primary" href="/client/demandes/nouvelle">
              Créer ma première demande
            </Link>
          </div>
        )}

        <div className="request-list">
          {requests.slice(0, 5).map((request) => (
            <RequestCard request={request} key={request.id} />
          ))}
        </div>
      </section>
    </main>
  );
}
