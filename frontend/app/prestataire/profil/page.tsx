"use client";

import { useState } from "react";

import { useProviderSession } from "@/components/provider/provider-shell";
import { apiMutation, formatDate } from "@/lib/provider-api";

export default function ProviderProfilePage() {
  const { user, profile, refreshProfile } = useProviderSession();
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
    <main>
      <section className="provider-page-head">
        <div>
          <p className="page-kicker">Mon profil</p>
          <h1>{profile.display_name}</h1>
          <p>
            Informations validées par BKO Services, métiers couverts et zones
            d’intervention.
          </p>
        </div>
      </section>

      {message && <div className="form-success">{message}</div>}
      {error && <div className="inline-error">{error}</div>}

      <div className="profile-grid">
        <section className="detail-card">
          <p className="page-kicker">Disponibilité</p>
          <h2>Recevoir de nouvelles offres</h2>
          <div className="availability-control">
            <div>
              <span
                className={
                  profile.is_available
                    ? "availability-dot online"
                    : "availability-dot offline"
                }
              />
              <strong>{profile.is_available ? "Disponible" : "Indisponible"}</strong>
              <p>
                Ce réglage concerne seulement les nouvelles offres. Une
                intervention déjà attribuée reste accessible jusqu’à sa fin.
              </p>
            </div>
            <button
              className={profile.is_available ? "button-danger-ghost" : "button-primary"}
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
          </div>
        </section>

        <section className="detail-card">
          <p className="page-kicker">Compte vérifié</p>
          <h2>Informations professionnelles</h2>
          <dl className="detail-list">
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
          {profile.description && (
            <div className="description-box">
              <strong>Présentation</strong>
              <p>{profile.description}</p>
            </div>
          )}
        </section>
      </div>

      <div className="provider-profile-lists">
        <section className="detail-card">
          <p className="page-kicker">Compétences</p>
          <h2>Métiers</h2>
          <div className="tag-list">
            {profile.trade_details.map((trade) => (
              <span className="provider-tag" key={trade.id}>{trade.name}</span>
            ))}
          </div>
        </section>

        <section className="detail-card">
          <p className="page-kicker">Couverture</p>
          <h2>Quartiers desservis</h2>
          <div className="tag-list">
            {profile.service_area_details.map((area) => (
              <span className="provider-tag" key={area.id}>
                {area.name} · {area.commune_name}
              </span>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
