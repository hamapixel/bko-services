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
    <main className="provider-dashboard-premium">
      <section className="role-welcome-card provider-welcome-card">
        <div className="role-welcome-copy">
          <span className="role-welcome-kicker">
            {profile.is_available && subscription?.status === "ACTIVE" ? "Disponible maintenant" : profile.is_available ? "Disponible · abonnement requis" : "Mode indisponible"}
          </span>
          <h1>Bonjour {profile.display_name} 👋</h1>
          <p>
            Gérez vos offres, vos interventions et votre disponibilité depuis
            un seul espace professionnel.
          </p>
          <div className="role-welcome-actions">
            <Link className="role-primary-action" href={subscription?.status === "ACTIVE" ? "/prestataire/offres" : "/prestataire/abonnement"}>
              {subscription?.status === "ACTIVE" ? "Voir mes offres" : "Choisir un abonnement"}
            </Link>
            <Link className="role-secondary-action" href="/prestataire/profil">
              Gérer mon profil
            </Link>
          </div>
        </div>

        <div className="provider-welcome-status" aria-hidden="true">
          <div className="provider-status-ring">
            <span className={profile.is_available ? "online" : "offline"} />
            <strong>{profile.is_available ? "Disponible" : "Indisponible"}</strong>
            <small>Nouvelles offres</small>
          </div>
        </div>
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

      {!loading && !error && subscription?.status !== "ACTIVE" && (
        <section className="dashboard-callout warning-card">
          <div>
            <strong>Votre abonnement ne permet pas encore de recevoir des demandes.</strong>
            <p>Un abonnement actif est nécessaire pour que les demandes de votre métier et de vos quartiers apparaissent ici.</p>
          </div>
          <Link className="button-secondary" href="/prestataire/abonnement">
            Voir mon abonnement
          </Link>
        </section>
      )}

      <section className="role-metric-grid">
        <article className="role-metric-card">
          <span className="role-metric-icon">✦</span>
          <div>
            <small>Offres en attente</small>
            <strong>{offerCount}</strong>
            <span>Encore acceptables</span>
          </div>
        </article>
        <article className="role-metric-card">
          <span className="role-metric-icon">↗</span>
          <div>
            <small>Interventions actives</small>
            <strong>{activeCount}</strong>
            <span>Attribuées ou en cours</span>
          </div>
        </article>
        <article className="role-metric-card">
          <span className="role-metric-icon">✓</span>
          <div>
            <small>À confirmer</small>
            <strong>{waitingClientCount}</strong>
            <span>En attente du client</span>
          </div>
        </article>
        <article className="role-metric-card">
          <span className="role-metric-icon">◇</span>
          <div>
            <small>Abonnement</small>
            <strong className="role-metric-text">
              {subscription?.status === "ACTIVE" ? "Actif" : "Non actif"}
            </strong>
            <span>{subscription?.plan.name ?? "Aucun plan actif"}</span>
          </div>
        </article>
      </section>

      {loading && <div className="skeleton-list">Chargement…</div>}
      {error && <div className="inline-error">{error}</div>}

      {!loading && !error && (
        <section className="content-section role-content-card">
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
