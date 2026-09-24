"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import ProviderOfferCard from "@/components/provider/provider-offer-card";
import { useProviderSession } from "@/components/provider/provider-shell";
import {
  apiGet,
  type ApiPage,
  type ProviderIntervention,
  type ProviderOffer,
  type ProviderSubscription,
} from "@/lib/provider-api";

export default function ProviderDashboardPage() {
  const { profile } = useProviderSession();
  const [offers, setOffers] = useState<ProviderOffer[]>([]);
  const [offerCount, setOfferCount] = useState(0);
  const [activeCount, setActiveCount] = useState(0);
  const [waitingClientCount, setWaitingClientCount] = useState(0);
  const [subscription, setSubscription] = useState<ProviderSubscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    Promise.all([
      apiGet<ApiPage<ProviderOffer>>("/api/v1/providers/offers/"),
      apiGet<ApiPage<ProviderIntervention>>(
        "/api/v1/providers/interventions/?status=ACCEPTED,EN_ROUTE,ARRIVED,IN_PROGRESS",
      ),
      apiGet<ApiPage<ProviderIntervention>>(
        "/api/v1/providers/interventions/?status=PROVIDER_COMPLETED",
      ),
      apiGet<{ subscription: ProviderSubscription | null }>(
        "/api/v1/subscriptions/me/",
      ),
    ])
      .then(([offerPage, activePage, waitingPage, subscriptionPayload]) => {
        if (!active) return;
        setOffers(offerPage.results);
        setOfferCount(offerPage.count);
        setActiveCount(activePage.count);
        setWaitingClientCount(waitingPage.count);
        setSubscription(subscriptionPayload.subscription);
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

  return (
    <main>
      <section className="provider-page-head">
        <div>
          <p className="page-kicker">Bonjour</p>
          <h1>{profile.display_name}</h1>
          <p>
            Gérez votre disponibilité, vos nouvelles offres et les interventions
            qui vous sont attribuées.
          </p>
        </div>
        <Link className="button-secondary" href="/prestataire/profil">
          Gérer ma disponibilité
        </Link>
      </section>

      {!profile.is_available && (
        <section className="dashboard-callout warning-card">
          <div>
            <strong>Vous êtes actuellement indisponible.</strong>
            <p>Vous ne recevrez pas de nouvelles offres tant que ce statut reste désactivé.</p>
          </div>
          <Link className="button-secondary" href="/prestataire/profil">
            Me rendre disponible
          </Link>
        </section>
      )}

      <section className="metric-grid">
        <article className="metric-card">
          <span>Offres en attente</span>
          <strong>{offerCount}</strong>
          <small>Offres encore acceptables</small>
        </article>
        <article className="metric-card">
          <span>Interventions actives</span>
          <strong>{activeCount}</strong>
          <small>Attribuées ou en cours</small>
        </article>
        <article className="metric-card">
          <span>À confirmer par le client</span>
          <strong>{waitingClientCount}</strong>
          <small>Terminées de votre côté</small>
        </article>
        <article className="metric-card">
          <span>Abonnement</span>
          <strong>{subscription?.status === "ACTIVE" ? "Actif" : "Non actif"}</strong>
          <small>{subscription?.plan.name ?? "Aucun plan actif"}</small>
        </article>
      </section>

      {loading && <div className="skeleton-list">Chargement…</div>}
      {error && <div className="inline-error">{error}</div>}

      {!loading && !error && (
        <section className="content-section">
          <div className="section-heading">
            <div>
              <p className="page-kicker">Nouvelles missions</p>
              <h2>Offres récentes</h2>
            </div>
            <Link className="text-link" href="/prestataire/offres">
              Voir toutes
            </Link>
          </div>

          {offers.length === 0 ? (
            <div className="empty-state compact">
              <strong>Aucune offre en attente</strong>
              <p>
                Les offres compatibles apparaîtront ici lorsque votre profil,
                disponibilité et abonnement le permettent.
              </p>
            </div>
          ) : (
            <div className="provider-offer-grid">
              {offers.slice(0, 4).map((offer) => (
                <ProviderOfferCard offer={offer} key={offer.id} />
              ))}
            </div>
          )}
        </section>
      )}
    </main>
  );
}
