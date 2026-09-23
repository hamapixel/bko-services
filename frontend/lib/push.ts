type PushConfig = {
  enabled: boolean;
  publicKey: string;
};

type WebPushOptions = {
  apiBaseUrl?: string;
  csrfToken: string;
};

function apiUrl(apiBaseUrl: string | undefined, path: string) {
  return `${(apiBaseUrl ?? "").replace(/\/$/, "")}${path}`;
}

function urlBase64ToUint8Array(value: string) {
  const padding = "=".repeat((4 - (value.length % 4)) % 4);
  const normalized = (value + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = window.atob(normalized);
  return Uint8Array.from(raw, (character) => character.charCodeAt(0));
}

async function fetchPushConfig(apiBaseUrl?: string): Promise<PushConfig> {
  const response = await fetch(
    apiUrl(apiBaseUrl, "/api/v1/notifications/push/config/"),
    {
      credentials: "include",
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error("Impossible de charger la configuration Web Push.");
  }

  return response.json() as Promise<PushConfig>;
}

export function webPushSupported() {
  return (
    typeof window !== "undefined" &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window
  );
}

export async function enableWebPush({
  apiBaseUrl,
  csrfToken,
}: WebPushOptions) {
  if (!webPushSupported()) {
    throw new Error("Le Web Push n'est pas pris en charge sur ce navigateur.");
  }

  const config = await fetchPushConfig(apiBaseUrl);
  if (!config.enabled || !config.publicKey) {
    throw new Error("Le Web Push n'est pas encore configuré sur le serveur.");
  }

  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    throw new Error("La permission de notification n'a pas été accordée.");
  }

  await navigator.serviceWorker.register("/sw.js");
  const registration = await navigator.serviceWorker.ready;

  let subscription = await registration.pushManager.getSubscription();
  if (!subscription) {
    subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(config.publicKey),
    });
  }

  const serialized = subscription.toJSON();
  if (!serialized.endpoint || !serialized.keys?.p256dh || !serialized.keys?.auth) {
    throw new Error("L'abonnement push retourné par le navigateur est incomplet.");
  }

  const response = await fetch(
    apiUrl(apiBaseUrl, "/api/v1/notifications/push/subscriptions/"),
    {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify({
        endpoint: serialized.endpoint,
        keys: {
          p256dh: serialized.keys.p256dh,
          auth: serialized.keys.auth,
        },
      }),
    },
  );

  if (!response.ok) {
    await subscription.unsubscribe();
    throw new Error("Le serveur n'a pas pu enregistrer l'abonnement Web Push.");
  }

  return subscription;
}

export async function disableWebPush({
  apiBaseUrl,
  csrfToken,
}: WebPushOptions) {
  if (!webPushSupported()) {
    return false;
  }

  const registration = await navigator.serviceWorker.getRegistration();
  if (!registration) {
    return false;
  }

  const subscription = await registration.pushManager.getSubscription();
  if (!subscription) {
    return false;
  }

  const response = await fetch(
    apiUrl(apiBaseUrl, "/api/v1/notifications/push/subscriptions/"),
    {
      method: "DELETE",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify({ endpoint: subscription.endpoint }),
    },
  );

  if (!response.ok && response.status !== 404) {
    throw new Error("Le serveur n'a pas pu désactiver l'abonnement Web Push.");
  }

  await subscription.unsubscribe();
  return true;
}
