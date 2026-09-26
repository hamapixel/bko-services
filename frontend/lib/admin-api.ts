import {
  apiGet,
  apiMutation,
  formatDate,
  type ApiPage,
  type PublicUser,
  type RequestStatus,
} from "@/lib/client-api";
import type {
  PaymentTransaction,
  ProviderAreaDetail,
  ProviderTradeDetail,
  SubscriptionHistory,
  SubscriptionPlan,
} from "@/lib/provider-api";

export { apiGet, apiMutation, formatDate };
export type { ApiPage, PublicUser, RequestStatus };

export type AdminCapabilities = {
  users: boolean;
  providers: boolean;
  requests: boolean;
  dispatch_requests: boolean;
  complaints: boolean;
  payments: boolean;
  subscriptions: boolean;
};

export type AdminOverview = {
  users_total: number;
  providers_pending: number;
  providers_verified: number;
  requests_active: number;
  complaints_open: number;
  payments_pending: number;
  payments_unfulfilled: number;
  subscriptions_effective: number;
  capabilities: AdminCapabilities;
};

export type AdminUser = {
  id: string;
  phone: string;
  first_name: string;
  last_name: string;
  email: string;
  role: "CLIENT" | "PROVIDER" | "ADMIN" | "SUPERADMIN";
  is_active: boolean;
  is_staff: boolean;
  phone_verified_at: string | null;
  date_joined: string;
  last_login: string | null;
};

export type AdminProviderReview = {
  id: string;
  reviewer_id: string;
  decision: "APPROVED" | "REJECTED" | "SUSPENDED" | "REOPENED";
  note: string;
  created_at: string;
};

export type AdminProvider = {
  id: string;
  user_id: string;
  user_phone: string;
  user_phone_verified_at: string | null;
  user_is_active: boolean;
  legal_name: string;
  display_name: string;
  description: string;
  trade_details: ProviderTradeDetail[];
  service_area_details: ProviderAreaDetail[];
  status: "PENDING" | "VERIFIED" | "REJECTED" | "SUSPENDED";
  is_available: boolean;
  identity_checked: boolean;
  review_note: string;
  verified_at: string | null;
  created_at: string;
  updated_at: string;
  reviews: AdminProviderReview[];
};

export type AdminRequestRow = {
  id: string;
  trade_name: string;
  neighborhood_name: string;
  commune_name: string;
  priority: "NORMAL" | "URGENT";
  status: RequestStatus;
  client_id: string;
  assigned_provider_id: string | null;
  assigned_provider_display_name: string | null;
  created_at: string;
  updated_at: string;
};

export type AdminRequestDetail = AdminRequestRow & {
  client_phone: string;
  title: string;
  description: string;
  address_detail: string;
  status_history: Array<{
    previous_status: string;
    new_status: RequestStatus;
    actor_id: string;
    created_at: string;
  }>;
  offers: Array<{
    id: string;
    provider_id: string;
    provider_display_name: string;
    status: "PENDING" | "ACCEPTED" | "DECLINED" | "EXPIRED" | "CANCELLED";
    created_at: string;
  }>;
};

export type AdminComplaint = {
  id: string;
  service_request_id: string;
  category: "SERVICE_QUALITY" | "BEHAVIOR" | "PAYMENT" | "SAFETY" | "OTHER";
  description: string;
  status: "OPEN" | "UNDER_REVIEW" | "RESOLVED" | "REJECTED";
  resolution_note: string;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  reporter_id: string;
  reporter_role: string;
  previous_request_status: RequestStatus;
  status_history: Array<{
    previous_status: string;
    new_status: "OPEN" | "UNDER_REVIEW" | "RESOLVED" | "REJECTED";
    note: string;
    created_at: string;
  }>;
};

export type AdminPayment = PaymentTransaction & {
  provider_id: string;
  provider_display_name: string;
  provider_transaction_id: string | null;
};

export type AdminSubscription = {
  id: string;
  plan: SubscriptionPlan;
  status: "ACTIVE" | "CANCELLED" | "EXPIRED";
  starts_at: string;
  ends_at: string;
  cancelled_at: string | null;
  free_trial_used_at: string | null;
  history: SubscriptionHistory[];
  provider_id: string;
  provider_display_name: string;
  stored_status: "ACTIVE" | "CANCELLED" | "EXPIRED";
};

export const ADMIN_PROVIDER_STATUS_LABELS: Record<AdminProvider["status"], string> = {
  PENDING: "En attente",
  VERIFIED: "Vérifié",
  REJECTED: "Refusé",
  SUSPENDED: "Suspendu",
};

export const COMPLAINT_STATUS_LABELS: Record<AdminComplaint["status"], string> = {
  OPEN: "Ouverte",
  UNDER_REVIEW: "En examen",
  RESOLVED: "Résolue",
  REJECTED: "Rejetée",
};

export const COMPLAINT_CATEGORY_LABELS: Record<AdminComplaint["category"], string> = {
  SERVICE_QUALITY: "Qualité du service",
  BEHAVIOR: "Comportement",
  PAYMENT: "Paiement",
  SAFETY: "Sécurité",
  OTHER: "Autre",
};

export function adminStatusTone(value: string) {
  if (["VERIFIED", "RESOLVED", "SUCCEEDED", "CLIENT_CONFIRMED", "ACTIVE"].includes(value)) {
    return "success";
  }
  if (["REJECTED", "SUSPENDED", "FAILED", "CANCELLED"].includes(value)) {
    return "danger";
  }
  if (["PENDING", "OPEN", "UNDER_REVIEW", "PROVIDER_COMPLETED"].includes(value)) {
    return "warning";
  }
  return "active";
}


export type AdminSubscriptionProviderOption = {
  id: string;
  display_name: string;
  status: "VERIFIED";
  has_subscription: boolean;
  subscription_id: string | null;
};
