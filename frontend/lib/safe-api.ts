export class OfflineActionError extends Error {
  constructor() {
    super(
      "Action non envoyée : aucune connexion réseau. Conservez-la comme brouillon puis envoyez-la explicitement après reconnexion.",
    );
    this.name = "OfflineActionError";
  }
}

export class ApiMutationError extends Error {
  status: number;
  payload: unknown;

  constructor(status: number, message: string, payload: unknown) {
    super(message);
    this.name = "ApiMutationError";
    this.status = status;
    this.payload = payload;
  }
}

type JsonMutationOptions = {
  csrfToken: string;
  body?: unknown;
  apiBaseUrl?: string;
};

function apiUrl(apiBaseUrl: string | undefined, path: string) {
  return `${(apiBaseUrl ?? "").replace(/\/$/, "")}${path}`;
}

function extractMessage(payload: unknown, fallback: string) {
  if (!payload || typeof payload !== "object") {
    return fallback;
  }

  const record = payload as Record<string, unknown>;
  if (typeof record.detail === "string") {
    return record.detail;
  }

  for (const value of Object.values(record)) {
    if (typeof value === "string") {
      return value;
    }
    if (Array.isArray(value) && typeof value[0] === "string") {
      return value[0];
    }
  }

  return fallback;
}

export function networkAvailable() {
  return typeof navigator === "undefined" ? true : navigator.onLine;
}

export async function sendJsonMutation<T>(
  path: string,
  method: "POST" | "PATCH" | "PUT" | "DELETE",
  { csrfToken, body, apiBaseUrl }: JsonMutationOptions,
): Promise<T> {
  if (!networkAvailable()) {
    throw new OfflineActionError();
  }

  const response = await fetch(apiUrl(apiBaseUrl, path), {
    method,
    credentials: "include",
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (response.status === 204) {
    return undefined as T;
  }

  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    throw new ApiMutationError(
      response.status,
      extractMessage(payload, `Le serveur a refusé l'action (HTTP ${response.status}).`),
      payload,
    );
  }

  return payload as T;
}
