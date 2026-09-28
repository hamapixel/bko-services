"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { useAdminSession } from "@/components/admin/admin-shell";
import {
  apiGet,
  apiMutation,
  formatDate,
  type AdminRequestDetail,
} from "@/lib/admin-api";
import { STATUS_LABELS, statusTone } from "@/lib/client-api";
import { apiGetAll, type City, type Commune, type Neighborhood } from "@/lib/client-api";

type DispatchResponse = {
  offers_created: number;
  request: AdminRequestDetail;
};

export default function AdminRequestDetailPage() {
  const params = useParams<{ id: string }>();
  const { overview, refreshOverview } = useAdminSession();
  const [item, setItem] = useState<AdminRequestDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [cities, setCities] = useState<City[]>([]);
  const [communes, setCommunes] = useState<Commune[]>([]);
  const [neighborhoods, setNeighborhoods] = useState<Neighborhood[]>([]);
  const [cityId, setCityId] = useState("");
  const [communeId, setCommuneId] = useState("");
  const [neighborhoodId, setNeighborhoodId] = useState("");

  useEffect(() => {
    let active = true;
    apiGet<AdminRequestDetail>(`/api/v1/admin/requests/${params.id}/`)
      .then((data) => {
        if (active) setItem(data);
      })
      .catch((caught) => {
        if (!active) return;
        setError(
          caught instanceof Error ? caught.message : "Demande introuvable.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [params.id]);

  useEffect(() => {
    if (!item?.requested_region_id || item.status !== "LOCATION_PENDING") return;
    let active = true;
    apiGetAll<City>(`/api/v1/locations/cities/?region=${encodeURIComponent(item.requested_region_id)}`)
      .then((data) => { if (active) setCities(data); })
      .catch((caught) => { if (active) setError(caught instanceof Error ? caught.message : "Zones indisponibles."); });
    return () => { active = false; };
  }, [item?.requested_region_id, item?.status]);

  async function loadCities() {
    if (!item?.requested_region_id) return;
    try {
      setCities(await apiGetAll<City>(`/api/v1/locations/cities/?region=${encodeURIComponent(item.requested_region_id)}`));
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Zones indisponibles."); }
  }

  async function selectCity(value: string) {
    setCityId(value); setCommuneId(""); setNeighborhoodId(""); setCommunes([]); setNeighborhoods([]);
    if (value) {
      try { setCommunes(await apiGetAll<Commune>(`/api/v1/locations/communes/?city=${encodeURIComponent(value)}`)); }
      catch (caught) { setError(caught instanceof Error ? caught.message : "Communes indisponibles."); }
    }
  }

  async function selectCommune(value: string) {
    setCommuneId(value); setNeighborhoodId(""); setNeighborhoods([]);
    if (value) {
      try { setNeighborhoods(await apiGetAll<Neighborhood>(`/api/v1/locations/neighborhoods/?commune=${encodeURIComponent(value)}`)); }
      catch (caught) { setError(caught instanceof Error ? caught.message : "Quartiers indisponibles."); }
    }
  }

  async function resolveLocation() {
    if (!item || !neighborhoodId) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const resolved = await apiMutation<AdminRequestDetail>(
        `/api/v1/admin/requests/${item.id}/resolve-location/`, "POST", { neighborhood: neighborhoodId },
      );
      setItem(resolved);
      setMessage(resolved.offers.length ? "Zone validée ; offres envoyées aux prestataires compatibles." : "Zone validée ; aucun prestataire compatible pour le moment.");
      await refreshOverview();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Validation impossible."); }
    finally { setBusy(false); }
  }

  async function dispatch() {
    if (!item) return;
    if (!window.confirm("Lancer la recherche de prestataires compatibles ?")) {
      return;
    }

    setBusy(true);
    setError("");
    setMessage("");
    try {
      const result = await apiMutation<DispatchResponse>(
        `/api/v1/admin/requests/${item.id}/dispatch/`,
        "POST",
        {},
      );
      setItem(result.request);
      setMessage(
        result.offers_created > 0
          ? `${result.offers_created} offre(s) créée(s).`
          : "Aucun prestataire compatible disponible pour le moment.",
      );
      await refreshOverview();
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Matching impossible.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <div className="skeleton-list">Chargement…</div>;
  if (!item) {
    return (
      <div className="empty-state">
        <strong>Demande indisponible</strong>
        <p>{error}</p>
        <Link className="button-secondary" href="/admin/demandes">
          Retour
        </Link>
      </div>
    );
  }

  const canDispatch =
    overview.capabilities.dispatch_requests &&
    (item.status === "CREATED" || item.status === "SEARCHING") &&
    item.offers.length === 0;

  return (
    <main>
      <section className="admin-page-head">
        <div>
          <Link className="back-link" href="/admin/demandes">
            ← Demandes
          </Link>
          <p className="page-kicker">{item.trade_name}</p>
          <h1>{item.title}</h1>
          <div className="detail-badges">
            <span className={`status-badge ${statusTone(item.status)}`}>
              {STATUS_LABELS[item.status]}
            </span>
            {item.priority === "URGENT" && (
              <span className="urgent-label">Urgente</span>
            )}
          </div>
        </div>
        {canDispatch && (
          <button
            className="button-primary"
            disabled={busy}
            type="button"
            onClick={dispatch}
          >
            {busy ? "Recherche…" : "Lancer le matching"}
          </button>
        )}
      </section>

      {message && <div className="form-success">{message}</div>}
      {error && <div className="inline-error">{error}</div>}
      {item.status === "LOCATION_PENDING" && (
        <section className="detail-card">
          <h2>Vérifier la zone demandée</h2>
          <p>Le client a indiqué : {item.requested_city}, {item.commune_name}, {item.neighborhood_name} ({item.region_name}). Vérifiez les lieux et créez-les dans l’administration des lieux si nécessaire. Aucune offre n’a été envoyée.</p>
          {overview.capabilities.dispatch_requests && (
            <div className="form-stack">
              <button className="button-secondary" type="button" onClick={() => void loadCities()}>Actualiser les lieux</button>
              <label className="field"><span>Ville vérifiée</span><select value={cityId} onChange={(event) => void selectCity(event.target.value)}><option value="">Choisir</option>{cities.map((city) => <option key={city.id} value={city.id}>{city.name}</option>)}</select></label>
              <label className="field"><span>Commune vérifiée</span><select disabled={!cityId} value={communeId} onChange={(event) => void selectCommune(event.target.value)}><option value="">Choisir</option>{communes.map((commune) => <option key={commune.id} value={commune.id}>{commune.name}</option>)}</select></label>
              <label className="field"><span>Quartier vérifié</span><select disabled={!communeId} value={neighborhoodId} onChange={(event) => setNeighborhoodId(event.target.value)}><option value="">Choisir</option>{neighborhoods.map((area) => <option key={area.id} value={area.id}>{area.name}</option>)}</select></label>
              <button className="button-primary" type="button" disabled={busy || !neighborhoodId} onClick={() => void resolveLocation()}>Valider la zone et rechercher</button>
            </div>
          )}
        </section>
      )}

      <div className="detail-grid">
        <div className="detail-main">
          <section className="detail-card">
            <h2>Données de la demande</h2>
            <dl className="detail-list">
              <div><dt>Client</dt><dd>{item.client_phone}</dd></div>
              <div>
                <dt>Zone</dt>
                <dd>{item.neighborhood_name}, {item.commune_name} · {item.requested_city || item.region_name}</dd>
              </div>
              <div><dt>Adresse</dt><dd>{item.address_detail}</dd></div>
              <div><dt>Créée le</dt><dd>{formatDate(item.created_at)}</dd></div>
            </dl>
            <div className="description-box">
              <strong>Description</strong>
              <p>{item.description}</p>
            </div>
          </section>

          <section className="detail-card">
            <h2>Historique des statuts</h2>
            <div className="timeline">
              {item.status_history.map((history, index) => (
                <div className="timeline-item" key={`${history.created_at}-${index}`}>
                  <span className="timeline-dot" />
                  <div>
                    <strong>{STATUS_LABELS[history.new_status]}</strong>
                    <small>{formatDate(history.created_at)}</small>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>

        <aside className="detail-side">
          <section className="admin-action-card">
            <p className="page-kicker">Attribution</p>
            <h2>Prestataire</h2>
            {item.assigned_provider_display_name ? (
              <p>{item.assigned_provider_display_name}</p>
            ) : (
              <p>Aucun prestataire attribué.</p>
            )}
          </section>

          <section className="detail-card">
            <h2>Offres générées</h2>
            {item.offers.length === 0 ? (
              <p className="muted-copy">Aucune offre.</p>
            ) : (
              <div className="admin-compact-list">
                {item.offers.map((offer) => (
                  <div key={offer.id}>
                    <strong>{offer.provider_display_name}</strong>
                    <span className={`status-badge ${statusTone(
                      offer.status === "ACCEPTED" ? "ACCEPTED" : "OFFERED",
                    )}`}>
                      {offer.status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="security-note">
            <strong>Données privées</strong>
            <p>
              Le téléphone, l’adresse et les textes libres n’apparaissent que
              dans cette fiche réservée aux administrateurs autorisés.
            </p>
          </section>
        </aside>
      </div>
    </main>
  );
}
