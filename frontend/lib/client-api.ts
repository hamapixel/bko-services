import { networkAvailable, OfflineActionError, sendJsonMutation } from "@/lib/safe-api";

export type ApiPage<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type PublicUser = {
  id: string;
  phone: string;
  first_name: string;
  last_name: string;
  email: string;
  role: "CLIENT" | "PROVIDER" | "ADMIN" | "SUPERADMIN";
  phone_verified_at: string | null;
  has_avatar: boolean;
  avatar_url: string | null;
};

export type Category = {
  id: string;
  name: string;
  description: string;
};

export type Trade = {
  id: string;
  name: string;
  description: string;
  category: string;
};

export type City = {
  id: string;
  name: string;
};

export type Commune = {
  id: string;
  name: string;
  city: string;
};

export type Neighborhood = {
  id: string;
  name: string;
  commune: string;
};

export type RequestStatus =
  | "CREATED"
  | "SEARCHING"
  | "OFFERED"
  | "ACCEPTED"
  | "EN_ROUTE"
  | "ARRIVED"
  | "IN_PROGRESS"
  | "PROVIDER_COMPLETED"
  | "CLIENT_CONFIRMED"
  | "CANCELLED"
  | "DISPUTED";

export type RequestHistoryItem = {
  previous_status: string;
  new_status: RequestStatus;
  created_at: string;
};

export type ServiceRequest = {
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
  has_review: boolean;
  assigned_provider_id?: string;
  assigned_provider_display_name?: string;
  assigned_provider_phone?: string;
  created_at: string;
  updated_at: string;
  status_history: RequestHistoryItem[];
};

export type Review = {
  id: string;
  request_id: string;
  provider_id: string;
  rating: number;
  comment: string;
  created_at: string;
};

export class ApiReadError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiReadError";
    this.status = status;
  }
}

async function readJson<T>(response: Response): Promise<T> {
  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const detail =
      payload &&
      typeof payload === "object" &&
      typeof (payload as Record<string, unknown>).detail === "string"
        ? String((payload as Record<string, unknown>).detail)
        : `Erreur serveur (HTTP ${response.status}).`;

    throw new ApiReadError(response.status, detail);
  }

  return payload as T;
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(path, {
    method: "GET",
    credentials: "include",
    cache: "no-store",
  });
  return readJson<T>(response);
}

export async function getCsrfToken() {
  if (!networkAvailable()) {
    throw new OfflineActionError();
  }
  const payload = await apiGet<{ csrfToken: string }>("/api/v1/auth/csrf/");
  return payload.csrfToken;
}

export async function apiMutation<T>(
  path: string,
  method: "POST" | "PATCH" | "PUT" | "DELETE",
  body?: unknown,
) {
  if (!networkAvailable()) {
    throw new OfflineActionError();
  }
  const csrfToken = await getCsrfToken();
  return sendJsonMutation<T>(path, method, { csrfToken, body });
}

export async function apiFormMutation<T>(
  path: string,
  method: "POST" | "PUT" | "PATCH",
  formData: FormData,
) {
  if (!networkAvailable()) {
    throw new OfflineActionError();
  }

  const csrfToken = await getCsrfToken();
  const response = await fetch(path, {
    method,
    credentials: "include",
    cache: "no-store",
    headers: {
      "X-CSRFToken": csrfToken,
    },
    body: formData,
  });
  return readJson<T>(response);
}

export const STATUS_LABELS: Record<RequestStatus, string> = {
  CREATED: "Enregistrée",
  SEARCHING: "Recherche en cours",
  OFFERED: "Proposée aux prestataires",
  ACCEPTED: "Prestataire trouvé",
  EN_ROUTE: "Prestataire en route",
  ARRIVED: "Prestataire arrivé",
  IN_PROGRESS: "Intervention en cours",
  PROVIDER_COMPLETED: "À confirmer",
  CLIENT_CONFIRMED: "Terminée",
  CANCELLED: "Annulée",
  DISPUTED: "Contestée",
};

export function formatDate(value: string) {
  return new Intl.DateTimeFormat("fr-ML", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function statusTone(status: RequestStatus) {
  if (status === "CLIENT_CONFIRMED") return "success";
  if (status === "CANCELLED" || status === "DISPUTED") return "danger";
  if (status === "PROVIDER_COMPLETED") return "warning";
  if (status === "CREATED" || status === "SEARCHING" || status === "OFFERED") {
    return "neutral";
  }
  return "active";
}
