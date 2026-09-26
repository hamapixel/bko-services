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
  const [totalCount, setTotalCount] = useState(0);
  const [waitingCount, setWaitingCount] = useState(0);
  const [completedCount, setCompletedCount] = useState(0);
  const [draftCount, setDraftCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    Promise.all([
      apiGet<ApiPage<ServiceRequest>>("/api/v1/requests/"),
      apiGet<ApiPage<ServiceRequest>>(
        "/api/v1/requests/?status=PROVIDER_COMPLETED",
      ),
      apiGet<ApiPage<ServiceRequest>>(
        "/api/v1/requests/?status=CLIENT_CONFIRMED",
      ),
      listRequestDrafts(user.id).catch(() => []),
    ])
      .then(([allPage, waitingPage, completedPage, drafts]) => {
        if (!active) return;
        setRequests(allPage.results);
        setTotalCount(allPage.count);
        setWaitingCount(waitingPage.count);
        setCompletedCount(completedPage.count);
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
  }, [user.id]);

  const firstName = user.first_name || "Bienvenue";

  return (
    <main className="client-dashboard-premium">
      <section className="client-welcome-card">
        <div className="client-welcome-copy">
          <span className="client-welcome-kicker">Bonjour {firstName} 👋</span>
          <h1>Quel service vous faut-il aujourd’hui ?</h1>
          <p>
            Décrivez votre besoin en quelques secondes. BKO Services vous aide
            à suivre la demande jusqu’à la fin de l’intervention.
          </p>
          <div className="client-welcome-actions">
            <Link className="client-premium-primary" href="/client/demandes/nouvelle">
              <span aria-hidden="true">＋</span>
              Nouvelle demande
            </Link>
            <Link className="client-premium-secondary" href="/client/demandes">
              Voir mes demandes
            </Link>
          </div>
        </div>

        <div className="client-welcome-visual" aria-hidden="true">
          <div className="client-service-orb client-service-orb-one">⚡</div>
          <div className="client-service-orb client-service-orb-two">🔧</div>
          <div className="client-service-orb client-service-orb-three">❄</div>
          <div className="client-welcome-center">
            <span>B</span>
            <small>BKO Services</small>
          </div>
        </div>
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

      <section className="client-metric-grid" aria-label="Résumé">
        <article className="client-metric-card">
          <div className="client-metric-icon">▦</div>
          <div>
            <span>Total demandes</span>
            <strong>{totalCount}</strong>
            <small>Votre historique</small>
          </div>
        </article>
        <article className="client-metric-card">
          <div className="client-metric-icon">✓</div>
          <div>
            <span>À confirmer</span>
            <strong>{waitingCount}</strong>
            <small>En attente de votre validation</small>
          </div>
        </article>
        <article className="client-metric-card">
          <div className="client-metric-icon">★</div>
          <div>
            <span>Terminées</span>
            <strong>{completedCount}</strong>
            <small>Interventions confirmées</small>
          </div>
        </article>
        <article className="client-metric-card">
          <div className="client-metric-icon">✎</div>
          <div>
            <span>Brouillons</span>
            <strong>{draftCount}</strong>
            <small>Sur cet appareil</small>
          </div>
        </article>
      </section>

      <section className="content-section client-recent-section">
        <div className="section-heading">
          <div>
            <p className="page-kicker">Activité récente</p>
            <h2>Vos dernières demandes</h2>
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
          <div className="empty-state compact client-empty-premium">
            <span className="client-empty-icon" aria-hidden="true">＋</span>
            <strong>Aucune demande pour le moment</strong>
            <p>
              Votre prochaine intervention commencera ici.
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
