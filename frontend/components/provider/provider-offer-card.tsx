import Link from "next/link";

import { formatDate, type ProviderOffer } from "@/lib/provider-api";

const MATCH_SCOPE_LABELS: Record<ProviderOffer["match_scope"], string> = {
  QUARTIER: "Votre quartier prioritaire",
  COMMUNE: "Autre quartier de votre commune",
  DEPLACEMENT: "Déplacement autorisé vers cette commune",
  INCONNU: "Zone compatible",
};

export default function ProviderOfferCard({ offer }: { offer: ProviderOffer }) {
  return (
    <article className="provider-offer-card">
      <div className="provider-offer-card-head">
        <div>
          <span className="request-meta">
            {offer.trade_name} · {offer.commune_name}
          </span>
          <h3>{offer.trade_name} · {offer.neighborhood_name}</h3>
        </div>
        {offer.priority === "URGENT" && (
          <span className="urgent-label">Urgente</span>
        )}
      </div>
      <div className="request-card-details">
        <span>📍 {offer.neighborhood_name}</span>
        <span>🕒 {formatDate(offer.created_at)}</span>
      </div>
      <p className="provider-offer-zone-note">
        {MATCH_SCOPE_LABELS[offer.match_scope]}
        {offer.match_scope === "COMMUNE" ? " : vérifiez le trajet avant d’accepter." : ""}
        {offer.match_scope === "DEPLACEMENT" ? " : cette commune fait partie de vos déplacements autorisés." : ""}
      </p>
      <div className="provider-offer-privacy">
        Titre, description, adresse précise et téléphone masqués avant acceptation.
      </div>
      <Link
        className="button-primary"
        href={`/prestataire/offres/${offer.id}`}
      >
        Voir l’offre
      </Link>
    </article>
  );
}
