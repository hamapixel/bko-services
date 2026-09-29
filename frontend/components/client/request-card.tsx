import Link from "next/link";

import {
  formatDate,
  STATUS_LABELS,
  statusTone,
  type ServiceRequest,
} from "@/lib/client-api";

export default function RequestCard({
  request,
}: {
  request: ServiceRequest;
}) {
  return (
    <Link className="request-card" href={`/client/demandes/${request.id}`}>
      <div className="request-card-top">
        <div>
          <span className="request-meta">
            {request.trade_name} · {request.commune_name}
          </span>
          <h3>{request.title}</h3>
        </div>
        <span className={`status-badge ${statusTone(request.status)}`}>
          {STATUS_LABELS[request.status]}
        </span>
      </div>

      <div className="request-card-details">
        <span>📍 {request.neighborhood_name}</span>
        <span>🕒 {formatDate(request.created_at)}</span>
        {request.priority === "URGENT" && (
          <span className="urgent-label">Urgente</span>
        )}
      </div>

      {request.assigned_provider_display_name && (
        <div className="request-provider-line">
          <span className="provider-dot" aria-hidden="true" />
          Prestataire : <strong>{request.assigned_provider_display_name}</strong>
        </div>
      )}

      {request.status === "PROVIDER_COMPLETED" && (
        <span className="request-review-prompt">Confirmer la fin de l’intervention →</span>
      )}
      {request.status === "CLIENT_CONFIRMED" && !request.has_review && (
        <span className="request-review-prompt">
          ★ Laisser un avis sur {request.assigned_provider_display_name ?? "le prestataire"} →
        </span>
      )}
    </Link>
  );
}
