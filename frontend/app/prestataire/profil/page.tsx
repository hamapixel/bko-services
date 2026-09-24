"use client";
/* eslint-disable @next/next/no-img-element -- private authenticated avatar URLs intentionally bypass image optimization. */

import { useState } from "react";

import AccountProfileTools from "@/components/account/account-profile-tools";
import { useProviderSession } from "@/components/provider/provider-shell";
import { apiMutation, formatDate } from "@/lib/provider-api";

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
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

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
          ? "Vous êtes maintenant disponible pour de nouvelles offres."
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
                  ? "Vous pouvez recevoir de nouvelles propositions."
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
            <span className="page-kicker">Couverture</span>
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

      <AccountProfileTools
        user={user}
        refreshUser={refreshUser}
        titlePrefix="Profil prestataire"
      />
    </main>
  );
}
