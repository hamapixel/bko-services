import Link from "next/link";

import {
  formatDate,
  STATUS_LABELS,
  statusTone,
  type ProviderIntervention,
} from "@/lib/provider-api";

export default function ProviderInterventionCard({
  intervention,
}: {
  intervention: ProviderIntervention;
}) {
  return (
    <Link
      className="request-card"
      href={`/prestataire/interventions/${intervention.id}`}
    >
      <div className="request-card-top">
        <div>
          <span className="request-meta">
            {intervention.trade_name} · {intervention.commune_name}
          </span>
          <h3>{intervention.title}</h3>
        </div>
        <span className={`status-badge ${statusTone(intervention.status)}`}>
          {STATUS_LABELS[intervention.status]}
        </span>
      </div>
      <div className="request-card-details">
        <span>📍 {intervention.neighborhood_name}</span>
        <span>🕒 {formatDate(intervention.updated_at)}</span>
        {intervention.priority === "URGENT" && (
          <span className="urgent-label">Urgente</span>
        )}
      </div>
    </Link>
  );
}
