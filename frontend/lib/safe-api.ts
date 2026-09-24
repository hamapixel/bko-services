export class OfflineActionError extends Error {
  constructor() {
    super(
      "Action non envoyée : aucune connexion réseau. Conservez-la comme brouillon puis envoyez-la explicitement après reconnexion.",
    );
    this.name = "OfflineActionError";
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

  if (!response.ok) {
    throw new Error(`Le serveur a refusé l'action (HTTP ${response.status}).`);
  }

  return response.json() as Promise<T>;
}
