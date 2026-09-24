import Link from "next/link";

import { formatDate, type ProviderOffer } from "@/lib/provider-api";

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
      <div className="provider-offer-privacy">
        Adresse précise et téléphone masqués avant acceptation.
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
