import {
  apiGet,
  apiMutation,
  formatDate,
  STATUS_LABELS,
  statusTone,
  type ApiPage,
  type PublicUser,
  type RequestHistoryItem,
  type RequestStatus,
} from "@/lib/client-api";

export { apiGet, apiMutation, formatDate, STATUS_LABELS, statusTone };
export type { ApiPage, PublicUser, RequestHistoryItem, RequestStatus };

export type ProviderTradeDetail = {
  id: string;
  name: string;
};

export type ProviderAreaDetail = {
  id: string;
  name: string;
  commune_name: string;
};

export type ProviderProfile = {
  id: string;
  legal_name: string;
  display_name: string;
  description: string;
  trades: string[];
  service_areas: string[];
  trade_details: ProviderTradeDetail[];
  service_area_details: ProviderAreaDetail[];
  status: "PENDING" | "VERIFIED" | "REJECTED" | "SUSPENDED";
  is_available: boolean;
  verified_at: string | null;
};

export type ProviderOffer = {
  id: string;
  request_id: string;
  trade_id: string;
  trade_name: string;
  neighborhood_id: string;
  neighborhood_name: string;
  commune_name: string;
  priority: "NORMAL" | "URGENT";
  status: "PENDING" | "ACCEPTED" | "DECLINED" | "EXPIRED" | "CANCELLED";
  created_at: string;
};

export type ProviderIntervention = {
  id: string;
  trade: string;
  trade_name: string;
  neighborhood: string;
  neighborhood_name: string;
  commune_name: string;
  title: string;
  description: string;
  address_detail: string;
  priority: "NORMAL" | "URGENT";
  status: RequestStatus;
  client_phone: string;
  created_at: string;
  updated_at: string;
  status_history: RequestHistoryItem[];
};

export type SubscriptionPlan = {
  id: string;
  code: string;
  name: string;
  description: string;
  price_xof: number;
  duration_days: number;
  can_receive_requests: boolean;
  can_receive_urgent_requests: boolean;
};

export type SubscriptionHistory = {
  action: "ACTIVATED" | "RENEWED" | "CANCELLED" | "EXPIRED";
  plan_code: string;
  plan_name: string;
  starts_at: string;
  ends_at: string;
  note: string;
  created_at: string;
};

export type ProviderSubscription = {
  id: string;
  plan: SubscriptionPlan;
  status: "ACTIVE" | "CANCELLED" | "EXPIRED";
  starts_at: string;
  ends_at: string;
  cancelled_at: string | null;
  history: SubscriptionHistory[];
};

export type PaymentTransaction = {
  id: string;
  merchant_reference: string;
  purpose: "ACTIVATE" | "RENEW";
  payment_provider: string;
  amount_xof: number;
  currency: "XOF";
  plan_code_snapshot: string;
  plan_name_snapshot: string;
  duration_days_snapshot: number;
  status: "PENDING" | "SUCCEEDED" | "FAILED" | "CANCELLED";
  confirmed_at: string | null;
  fulfilled_at: string | null;
  fulfillment_error_code: string;
  created_at: string;
  updated_at: string;
};

export type PublicReview = {
  id: string;
  rating: number;
  comment: string;
  created_at: string;
};

export const PROVIDER_STATUS_LABELS: Record<ProviderProfile["status"], string> = {
  PENDING: "En attente",
  VERIFIED: "Vérifié",
  REJECTED: "Refusé",
  SUSPENDED: "Suspendu",
};

export const PAYMENT_STATUS_LABELS: Record<PaymentTransaction["status"], string> = {
  PENDING: "En attente",
  SUCCEEDED: "Confirmé",
  FAILED: "Échoué",
  CANCELLED: "Annulé",
};

export function formatXof(value: number) {
  return new Intl.NumberFormat("fr-FR").format(value) + " FCFA";
}

export function nextProviderStatus(status: RequestStatus): RequestStatus | null {
  const next: Partial<Record<RequestStatus, RequestStatus>> = {
    ACCEPTED: "EN_ROUTE",
    EN_ROUTE: "ARRIVED",
    ARRIVED: "IN_PROGRESS",
    IN_PROGRESS: "PROVIDER_COMPLETED",
  };
  return next[status] ?? null;
}

export const PROVIDER_ACTION_LABELS: Partial<Record<RequestStatus, string>> = {
  EN_ROUTE: "Je suis en route",
  ARRIVED: "Je suis arrivé",
  IN_PROGRESS: "Commencer l’intervention",
  PROVIDER_COMPLETED: "Marquer comme terminée",
};
