"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{
    outcome: "accepted" | "dismissed";
    platform: string;
  }>;
};

type NavigatorWithStandalone = Navigator & {
  standalone?: boolean;
};

function isIosDevice() {
  if (typeof window === "undefined") {
    return false;
  }

  return /iphone|ipad|ipod/i.test(window.navigator.userAgent);
}

function isInstalled() {
  if (typeof window === "undefined") {
    return false;
  }

  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    Boolean((window.navigator as NavigatorWithStandalone).standalone)
  );
}

function subscribeNetwork(callback: () => void) {
  window.addEventListener("online", callback);
  window.addEventListener("offline", callback);
  return () => {
    window.removeEventListener("online", callback);
    window.removeEventListener("offline", callback);
  };
}

function getNetworkSnapshot() {
  return navigator.onLine;
}

function getServerNetworkSnapshot() {
  return true;
}

function subscribeInstalled(callback: () => void) {
  window.addEventListener("appinstalled", callback);
  const media = window.matchMedia("(display-mode: standalone)");
  media.addEventListener("change", callback);

  return () => {
    window.removeEventListener("appinstalled", callback);
    media.removeEventListener("change", callback);
  };
}

function getInstalledSnapshot() {
  return isInstalled();
}

function getServerInstalledSnapshot() {
  return false;
}

function subscribeEnvironment() {
  return () => undefined;
}

function getIosSnapshot() {
  return isIosDevice();
}

function getServerIosSnapshot() {
  return false;
}

export default function PwaClient() {
  const online = useSyncExternalStore(
    subscribeNetwork,
    getNetworkSnapshot,
    getServerNetworkSnapshot,
  );
  const installed = useSyncExternalStore(
    subscribeInstalled,
    getInstalledSnapshot,
    getServerInstalledSnapshot,
  );
  const [installPrompt, setInstallPrompt] =
    useState<BeforeInstallPromptEvent | null>(null);
  const iosDevice = useSyncExternalStore(
    subscribeEnvironment,
    getIosSnapshot,
    getServerIosSnapshot,
  );
  const [updateReady, setUpdateReady] = useState(false);
  const registrationRef = useRef<ServiceWorkerRegistration | null>(null);
  const reloadOnControllerChange = useRef(false);

  useEffect(() => {
    const onInstalled = () => {
      setInstallPrompt(null);
    };
    const onBeforeInstallPrompt = (event: Event) => {
      const installEvent = event as BeforeInstallPromptEvent;
      installEvent.preventDefault();
      setInstallPrompt(installEvent);
    };

    window.addEventListener("appinstalled", onInstalled);
    window.addEventListener("beforeinstallprompt", onBeforeInstallPrompt);

    if ("serviceWorker" in navigator && window.isSecureContext) {
      // Never let a development service worker keep stale Next.js assets/CSS.
      // Production still keeps the installable PWA behavior.
      if (process.env.NODE_ENV !== "production") {
        navigator.serviceWorker.getRegistrations().then((registrations) => {
          registrations.forEach((registration) => registration.unregister());
        });
        if ("caches" in window) {
          caches.keys().then((keys) => {
            keys
              .filter((key) => key.startsWith("bko-services-"))
              .forEach((key) => caches.delete(key));
          });
        }

        return () => {
          window.removeEventListener("appinstalled", onInstalled);
          window.removeEventListener("beforeinstallprompt", onBeforeInstallPrompt);
        };
      }

      navigator.serviceWorker
        .register("/sw.js", { scope: "/" })
        .then((registration) => {
          registrationRef.current = registration;

          if (registration.waiting && navigator.serviceWorker.controller) {
            setUpdateReady(true);
          }

          registration.addEventListener("updatefound", () => {
            const installing = registration.installing;
            if (!installing) {
              return;
            }

            installing.addEventListener("statechange", () => {
              if (
                installing.state === "installed" &&
                navigator.serviceWorker.controller
              ) {
                setUpdateReady(true);
              }
            });
          });
        })
        .catch(() => {
          // The application remains usable in the browser if SW registration fails.
        });

      const onControllerChange = () => {
        if (reloadOnControllerChange.current) {
          window.location.reload();
        }
      };
      navigator.serviceWorker.addEventListener(
        "controllerchange",
        onControllerChange,
      );

      return () => {
        window.removeEventListener("appinstalled", onInstalled);
        window.removeEventListener(
          "beforeinstallprompt",
          onBeforeInstallPrompt,
        );
        navigator.serviceWorker.removeEventListener(
          "controllerchange",
          onControllerChange,
        );
      };
    }

    return () => {
      window.removeEventListener("appinstalled", onInstalled);
      window.removeEventListener("beforeinstallprompt", onBeforeInstallPrompt);
    };
  }, []);

  async function installApp() {
    if (!installPrompt) {
      return;
    }

    await installPrompt.prompt();
    await installPrompt.userChoice;
    setInstallPrompt(null);
  }

  function applyUpdate() {
    const waiting = registrationRef.current?.waiting;
    if (!waiting) {
      return;
    }

    reloadOnControllerChange.current = true;
    waiting.postMessage({ type: "SKIP_WAITING" });
  }

  if (online && installed && !updateReady) {
    return null;
  }

  return (
    <aside className="pwa-status" aria-live="polite">
      {!online && (
        <p className="pwa-status-message">
          Hors ligne — aucune action sensible ne sera déclarée envoyée.
        </p>
      )}

      {online && updateReady && (
        <button className="pwa-action" type="button" onClick={applyUpdate}>
          Mettre à jour
        </button>
      )}

      {online && !installed && installPrompt && (
        <button className="pwa-action" type="button" onClick={installApp}>
          Installer BKO Services
        </button>
      )}

      {online && !installed && !installPrompt && iosDevice && (
        <p className="pwa-status-message">
          iPhone/iPad : Partager → Sur l’écran d’accueil.
        </p>
      )}
    </aside>
  );
}
