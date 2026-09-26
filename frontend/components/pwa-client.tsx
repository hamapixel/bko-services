"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { usePathname } from "next/navigation";
import Image from "next/image";
import { apiGet, type PublicUser } from "@/lib/client-api";

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

const INSTALL_REMINDER_KEY = "bko-install-reminder-after";
const REMINDER_DELAY = 7 * 24 * 60 * 60 * 1000;

function expectedRole(pathname: string): PublicUser["role"] | "ADMINISTRATOR" | null {
  if (pathname === "/client" || pathname.startsWith("/client/")) return "CLIENT";
  if (pathname === "/prestataire" || pathname.startsWith("/prestataire/")) {
    return pathname.startsWith("/prestataire/connexion") || pathname.startsWith("/prestataire/devenir")
      ? null
      : "PROVIDER";
  }
  if (pathname === "/admin" || pathname.startsWith("/admin/")) {
    return pathname.startsWith("/admin/connexion") ? null : "ADMINISTRATOR";
  }
  return null;
}

function deferInvitation() {
  try {
    localStorage.setItem(INSTALL_REMINDER_KEY, String(Date.now() + REMINDER_DELAY));
  } catch {
    // Private browsing may disable storage; the current dialog still closes.
  }
}

function reminderIsDue() {
  try {
    return Date.now() >= Number(localStorage.getItem(INSTALL_REMINDER_KEY) || 0);
  } catch {
    return true;
  }
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

export default function PwaClient() {
  const pathname = usePathname();
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
  const [updateReady, setUpdateReady] = useState(false);
  const [showInvitation, setShowInvitation] = useState(false);
  const [isIos, setIsIos] = useState(false);
  const registrationRef = useRef<ServiceWorkerRegistration | null>(null);
  const reloadOnControllerChange = useRef(false);
  const dialogRef = useRef<HTMLElement | null>(null);
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const installButtonRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    const onInstalled = () => {
      setInstallPrompt(null);
      setShowInvitation(false);
      deferInvitation();
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

  useEffect(() => {
    const role = expectedRole(pathname);
    const ios = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
      (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
    const android = /Android/i.test(navigator.userAgent);
    if (
      process.env.NODE_ENV !== "production" || !role || !online || installed ||
      updateReady || !window.isSecureContext || !reminderIsDue() ||
      !(installPrompt || ios || android)
    ) {
      return;
    }

    let cancelled = false;
    let timer: number | undefined;
    apiGet<PublicUser>("/api/v1/auth/me/")
      .then((user) => {
        if (cancelled || !(user.role === role ||
          (role === "ADMINISTRATOR" && ["ADMIN", "SUPERADMIN"].includes(user.role)))) return;
        timer = window.setTimeout(() => {
          if (!cancelled && reminderIsDue()) {
            setIsIos(ios);
            setShowInvitation(true);
          }
        }, 1200);
      })
      .catch(() => {
        // Do not display an install invitation without a confirmed session.
      });

    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [pathname, online, installed, updateReady, installPrompt]);

  function closeInvitation() {
    deferInvitation();
    setShowInvitation(false);
  }

  useEffect(() => {
    if (!showInvitation) return;
    const previousFocus = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;
    (installPrompt ? installButtonRef.current : closeButtonRef.current)?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeInvitation();
      if (event.key !== "Tab" || !dialogRef.current) return;
      const buttons = Array.from(dialogRef.current.querySelectorAll("button"));
      const first = buttons[0];
      const last = buttons[buttons.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      previousFocus?.focus();
    };
  }, [showInvitation, installPrompt]);

  async function installApp() {
    if (!installPrompt) {
      return;
    }

    try {
      await installPrompt.prompt();
      await installPrompt.userChoice;
    } catch {
      // Browser prompts can be cancelled or made unavailable between events.
    } finally {
      setInstallPrompt(null);
      closeInvitation();
    }
  }

  function applyUpdate() {
    const waiting = registrationRef.current?.waiting;
    if (!waiting) {
      return;
    }

    reloadOnControllerChange.current = true;
    waiting.postMessage({ type: "SKIP_WAITING" });
  }

  const invitationVisible = showInvitation && online && !installed && !updateReady && Boolean(expectedRole(pathname));
  if (online && !updateReady && !invitationVisible) {
    return null;
  }

  return (
    <>
      {(!online || updateReady) && <aside className="pwa-status" aria-live="polite">
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
      </aside>}

      {invitationVisible && (
        <div className="pwa-install-overlay">
          <section ref={dialogRef} className="pwa-install-dialog" role="dialog" aria-modal="true" aria-labelledby="pwa-install-title" aria-describedby="pwa-install-description">
            <button ref={closeButtonRef} className="pwa-install-close" type="button" onClick={closeInvitation} aria-label="Fermer l’invitation">×</button>
            <Image src="/icons/icon-192.svg" width={66} height={66} alt="" className="pwa-install-icon" unoptimized />
            <p className="pwa-install-eyebrow">BKO SERVICES</p>
            <h2 id="pwa-install-title">Installer l’application</h2>
            <p id="pwa-install-description">Retrouvez vos demandes et vos interventions directement depuis votre écran d’accueil.</p>
            {!installPrompt && <p className="pwa-install-hint">
              {isIos
                ? "Dans votre navigateur, touchez Partager puis « Sur l’écran d’accueil »."
                : "Dans le menu de votre navigateur, choisissez « Installer l’application » ou « Ajouter à l’écran d’accueil »."}
            </p>}
            {installPrompt && <button ref={installButtonRef} className="pwa-install-primary" type="button" onClick={installApp}>Installer l’application</button>}
            <button className="pwa-install-later" type="button" onClick={closeInvitation}>{installPrompt ? "Plus tard" : "Compris, plus tard"}</button>
          </section>
        </div>
      )}
    </>
  );
}
