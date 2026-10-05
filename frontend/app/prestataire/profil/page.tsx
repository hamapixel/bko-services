"use client";
/* eslint-disable @next/next/no-img-element -- private authenticated avatar URLs intentionally bypass image optimization. */

import { useEffect, useState } from "react";

import AccountProfileTools from "@/components/account/account-profile-tools";
import { useProviderSession } from "@/components/provider/provider-shell";
import { apiGetAll, type Commune } from "@/lib/client-api";
import {
  apiGet,
  apiMutation,
  formatDate,
  type ProviderProfile,
  type ProviderSubscription,
} from "@/lib/provider-api";

function providerInitials(name: string) {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join("");
}

export default function ProviderProfilePage() {
  const { user, profile, refreshProfile, refreshUser } = useProviderSession();
  const [busy, setBusy] = useState(false);
  const [travelBusy, setTravelBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [communes, setCommunes] = useState<Commune[]>([]);
  const [communesLoading, setCommunesLoading] = useState(true);
  const [subscription, setSubscription] = useState<ProviderSubscription | null>(null);
  const [selectedTravelCommunes, setSelectedTravelCommunes] = useState<string[]>(
    profile.travel_communes,
  );

  useEffect(() => {
    let active = true;
    apiGetAll<Commune>("/api/v1/locations/communes/")
      .then((items) => {
        if (active) setCommunes(items);
      })
      .catch((caught) => {
        if (active) {
          setError(
            caught instanceof Error
              ? caught.message
              : "Impossible de charger les communes disponibles.",
          );
        }
      })
      .finally(() => {
        if (active) setCommunesLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    apiGet<{ subscription: ProviderSubscription | null }>(
      "/api/v1/subscriptions/me/",
    )
      .then((payload) => {
        if (active) setSubscription(payload.subscription);
      })
      .catch(() => {
        // Availability can still be managed; the backend remains authoritative.
      });
    return () => {
      active = false;
    };
  }, []);

  const subscriptionActive = subscription?.status === "ACTIVE";

  async function toggleAvailability() {
    setBusy(true);
    setMessage("");
    setError("");
    try {
      const result = await apiMutation<{ is_available: boolean }>(
        "/api/v1/providers/availability/",
        "PATCH",
        { is_available: !profile.is_available },
      );
      await refreshProfile();
      setMessage(
        result.is_available
          ? subscriptionActive
            ? "Vous êtes disponible. Votre abonnement est actif : vous pouvez recevoir de nouvelles offres compatibles."
            : "Vous êtes disponible. Activez un abonnement pour recevoir de nouvelles offres."
          : "Vous êtes maintenant indisponible pour les nouvelles offres.",
      );
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Impossible de modifier votre disponibilité.",
      );
    } finally {
      setBusy(false);
    }
  }

  function toggleTravelCommune(communeId: string) {
    setSelectedTravelCommunes((current) =>
      current.includes(communeId)
        ? current.filter((id) => id !== communeId)
        : [...current, communeId],
    );
  }

  async function saveTravelCommunes() {
    setTravelBusy(true);
    setMessage("");
    setError("");
    try {
      const result = await apiMutation<ProviderProfile>(
        "/api/v1/providers/travel-communes/",
        "PATCH",
        { commune_ids: selectedTravelCommunes },
      );
      setSelectedTravelCommunes(result.travel_communes);
      await refreshProfile();
      setMessage(
        selectedTravelCommunes.length
          ? "Communes de déplacement enregistrées. Elles seront utilisées en troisième priorité si aucun prestataire plus proche n'est trouvé."
          : "Aucune commune de déplacement supplémentaire n'est autorisée.",
      );
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Impossible d'enregistrer les communes de déplacement.",
      );
    } finally {
      setTravelBusy(false);
    }
  }

  return (
    <main className="premium-profile-page">
      <section className="premium-profile-hero provider-profile-hero">
        <div className="premium-profile-avatar">
          {user.has_avatar && user.avatar_url ? (
            <img src={user.avatar_url} alt={profile.display_name} />
          ) : (
            <span>{providerInitials(profile.display_name)}</span>
          )}
        </div>

        <div className="premium-profile-identity">
          <span className="premium-profile-role">Prestataire vérifié</span>
          <h1>{profile.display_name}</h1>
          <p>{profile.description || "Professionnel du réseau BKO Services."}</p>
          <div className="premium-profile-badges">
            <span>{user.phone}</span>
            <span className="verified">✓ Profil vérifié</span>
            <span className={profile.is_available ? "verified" : "pending"}>
              {profile.is_available ? "Disponible" : "Indisponible"}
            </span>
          </div>
        </div>

        <button
          className={profile.is_available ? "premium-profile-toggle danger" : "premium-profile-toggle"}
          disabled={busy}
          type="button"
          onClick={toggleAvailability}
        >
          {busy
            ? "Mise à jour…"
            : profile.is_available
              ? "Me rendre indisponible"
              : "Me rendre disponible"}
        </button>
      </section>

      {message && <div className="form-success premium-profile-message">{message}</div>}
      {error && <div className="inline-error premium-profile-message">{error}</div>}

      <div className="premium-profile-main-grid provider-premium-details">
        <section className="account-tool-card">
          <div className="account-tool-heading">
            <span className="page-kicker">Informations professionnelles</span>
            <h2>Identité validée</h2>
            <p>
              Ces informations ont été vérifiées par BKO Services et restent
              protégées par le processus de validation.
            </p>
          </div>

          <dl className="premium-definition-list">
            <div>
              <dt>Nom public</dt>
              <dd>{profile.display_name}</dd>
            </div>
            <div>
              <dt>Nom légal</dt>
              <dd>{profile.legal_name}</dd>
            </div>
            <div>
              <dt>Téléphone</dt>
              <dd>{user.phone}</dd>
            </div>
            <div>
              <dt>Vérifié le</dt>
              <dd>{profile.verified_at ? formatDate(profile.verified_at) : "—"}</dd>
            </div>
          </dl>
        </section>

        <section className="account-tool-card premium-availability-card">
          <div className="account-tool-heading">
            <span className="page-kicker">Disponibilité</span>
            <h2>Réception des offres</h2>
            <p>
              Vous pouvez couper les nouvelles offres sans interrompre les
              interventions déjà attribuées.
            </p>
          </div>

          <div className="premium-availability-status">
            <span
              className={
                profile.is_available
                  ? "premium-availability-dot online"
                  : "premium-availability-dot offline"
              }
            />
            <div>
              <strong>{profile.is_available ? "Disponible" : "Indisponible"}</strong>
              <small>
                {profile.is_available
                  ? subscriptionActive
                    ? "Votre abonnement est actif : vous pouvez recevoir de nouvelles offres compatibles."
                    : "Un abonnement actif est nécessaire pour recevoir de nouvelles offres."
                  : "Les nouvelles offres sont temporairement suspendues."}
              </small>
            </div>
          </div>
        </section>
      </div>

      <div className="provider-profile-lists premium-provider-lists">
        <section className="account-tool-card">
          <div className="account-tool-heading">
            <span className="page-kicker">Compétences</span>
            <h2>Métiers</h2>
          </div>
          <div className="tag-list">
            {profile.trade_details.map((trade) => (
              <span className="provider-tag" key={trade.id}>{trade.name}</span>
            ))}
          </div>
        </section>

        <section className="account-tool-card">
          <div className="account-tool-heading">
            <span className="page-kicker">Couverture principale</span>
            <h2>Quartiers desservis</h2>
          </div>
          <div className="tag-list">
            {profile.service_area_details.map((area) => (
              <span className="provider-tag" key={area.id}>
                {area.name} · {area.commune_name}
              </span>
            ))}
          </div>
        </section>
      </div>

      <section className="account-tool-card" style={{ marginTop: 24 }}>
        <div className="account-tool-heading">
          <span className="page-kicker">Déplacements autorisés</span>
          <h2>Autres communes où je peux intervenir</h2>
          <p>
            Le matching cherche d’abord votre quartier, puis votre commune. Ces communes
            ne sont utilisées qu’en troisième priorité lorsqu’il reste des places d’offre.
          </p>
        </div>

        {communesLoading ? (
          <p>Chargement des communes…</p>
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: 12,
              marginTop: 16,
            }}
          >
            {communes.map((commune) => {
              const checked = selectedTravelCommunes.includes(commune.id);
              return (
                <label
                  key={commune.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    padding: "12px 14px",
                    border: checked ? "1px solid #f27932" : "1px solid #dbe3ec",
                    borderRadius: 14,
                    cursor: "pointer",
                    background: checked ? "#fff7f1" : "#fff",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleTravelCommune(commune.id)}
                  />
                  <span>{commune.name}</span>
                </label>
              );
            })}
          </div>
        )}

        <div style={{ marginTop: 18, display: "flex", gap: 12, flexWrap: "wrap" }}>
          <button
            className="button-primary"
            type="button"
            disabled={travelBusy || communesLoading}
            onClick={saveTravelCommunes}
          >
            {travelBusy ? "Enregistrement…" : "Enregistrer mes communes"}
          </button>
          <small style={{ alignSelf: "center" }}>
            {selectedTravelCommunes.length} commune(s) supplémentaire(s) autorisée(s).
          </small>
        </div>

        {profile.travel_commune_details.length > 0 && (
          <div className="tag-list" style={{ marginTop: 18 }}>
            {profile.travel_commune_details.map((commune) => (
              <span className="provider-tag" key={commune.id}>
                {commune.name} · {commune.city_name}
              </span>
            ))}
          </div>
        )}
      </section>

      <AccountProfileTools
        user={user}
        refreshUser={refreshUser}
        titlePrefix="Profil prestataire"
      />
    </main>
  );
}
