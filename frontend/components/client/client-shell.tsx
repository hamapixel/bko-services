"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  ApiReadError,
  apiGet,
  apiMutation,
  type PublicUser,
} from "@/lib/client-api";

type ClientSessionValue = {
  user: PublicUser;
  refreshUser: () => Promise<void>;
};

const ClientSessionContext = createContext<ClientSessionValue | null>(null);

const NAVIGATION = [
  { href: "/client", label: "Accueil", icon: "⌂" },
  { href: "/client/demandes", label: "Demandes", icon: "≡" },
  { href: "/client/demandes/nouvelle", label: "Nouvelle demande", icon: "+" },
  { href: "/client/brouillons", label: "Brouillons", icon: "✎" },
  { href: "/client/profil", label: "Profil", icon: "●" },
];

export function useClientSession() {
  const context = useContext(ClientSessionContext);
  if (!context) {
    throw new Error("useClientSession doit être utilisé dans ClientShell.");
  }
  return context;
}

function navIsActive(pathname: string, href: string) {
  if (href === "/client") return pathname === href;
  if (href === "/client/demandes/nouvelle") {
    return pathname.startsWith("/client/demandes/nouvelle");
  }
  if (href === "/client/demandes") {
    return (
      pathname.startsWith("/client/demandes") &&
      !pathname.startsWith("/client/demandes/nouvelle")
    );
  }
  return pathname.startsWith(href);
}

function initials(user: PublicUser) {
  const source =
    [user.first_name, user.last_name].filter(Boolean).join(" ").trim() ||
    user.phone;
  return source
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join("");
}

export default function ClientShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<PublicUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [menuOpen, setMenuOpen] = useState(false);
  const [sessionError, setSessionError] = useState("");

  const loadUser = useCallback(async () => {
    const profile = await apiGet<PublicUser>("/api/v1/auth/me/");
    setUser(profile);
  }, []);

  useEffect(() => {
    let active = true;

    apiGet<PublicUser>("/api/v1/auth/me/")
      .then((profile) => {
        if (!active) return;
        setUser(profile);
        setSessionError("");
      })
      .catch((error: unknown) => {
        if (!active) return;
        if (error instanceof ApiReadError && (error.status === 401 || error.status === 403)) {
          router.replace("/connexion");
          return;
        }
        setSessionError(
          error instanceof Error
            ? error.message
            : "Impossible de charger votre session.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [router]);

  const contextValue = useMemo(
    () =>
      user
        ? {
            user,
            refreshUser: loadUser,
          }
        : null,
    [loadUser, user],
  );

  async function logout() {
    try {
      await apiMutation<void>("/api/v1/auth/logout/", "POST", {});
    } finally {
      router.replace("/connexion");
      router.refresh();
    }
  }

  if (loading) {
    return (
      <main className="client-loading">
        <div className="loading-spinner" aria-hidden="true" />
        <p>Chargement de votre espace…</p>
      </main>
    );
  }

  if (sessionError) {
    return (
      <main className="client-loading">
        <section className="empty-state">
          <strong>Connexion au serveur impossible</strong>
          <p>{sessionError}</p>
          <button className="button-primary" type="button" onClick={() => window.location.reload()}>
            Réessayer
          </button>
        </section>
      </main>
    );
  }

  if (!user || !contextValue) {
    return null;
  }

  if (user.role !== "CLIENT") {
    return (
      <main className="client-loading">
        <section className="empty-state">
          <strong>Espace réservé aux clients</strong>
          <p>Ce compte utilise le rôle {user.role}.</p>
          <button className="button-primary" type="button" onClick={logout}>
            Se déconnecter
          </button>
        </section>
      </main>
    );
  }

  return (
    <ClientSessionContext.Provider value={contextValue}>
      <div className="client-app">
        <aside className={`client-sidebar ${menuOpen ? "is-open" : ""}`}>
          <div className="client-sidebar-head">
            <Link className="client-brand" href="/client">
              <span className="brand-mark" aria-hidden="true">B</span>
              <span>
                <strong>BKO Services</strong>
                <small>Espace client</small>
              </span>
            </Link>
            <button
              className="icon-button mobile-only"
              type="button"
              aria-label="Fermer le menu"
              onClick={() => setMenuOpen(false)}
            >
              ×
            </button>
          </div>

          <nav className="client-nav" aria-label="Navigation client">
            {NAVIGATION.map((item) => {
              const active = navIsActive(pathname, item.href);
              return (
                <Link
                  className={active ? "client-nav-link active" : "client-nav-link"}
                  href={item.href}
                  key={item.href}
                  onClick={() => setMenuOpen(false)}
                >
                  <span className="client-nav-icon" aria-hidden="true">{item.icon}</span>
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>

          <div className="client-account-card">
            <span className="client-avatar">
              {user.has_avatar && user.avatar_url ? (
                <img src={user.avatar_url} alt="" />
              ) : (
                initials(user)
              )}
            </span>
            <span className="client-account-copy">
              <strong>
                {[user.first_name, user.last_name].filter(Boolean).join(" ") ||
                  "Client BKO"}
              </strong>
              <small>{user.phone}</small>
            </span>
            <button
              className="text-button"
              type="button"
              onClick={logout}
              aria-label="Se déconnecter"
            >
              Quitter
            </button>
          </div>
        </aside>

        {menuOpen && (
          <button
            className="client-menu-backdrop"
            type="button"
            aria-label="Fermer le menu"
            onClick={() => setMenuOpen(false)}
          />
        )}

        <div className="client-main">
          <header className="client-topbar">
            <button
              className="icon-button mobile-only"
              type="button"
              aria-label="Ouvrir le menu"
              onClick={() => setMenuOpen(true)}
            >
              ☰
            </button>
            <div className="client-topbar-title">
              <strong>BKO Services</strong>
              <small>Le bon professionnel, au bon moment.</small>
            </div>
            <Link className="client-mini-avatar" href="/client/profil" aria-label="Ouvrir mon profil">
              {user.has_avatar && user.avatar_url ? (
                <img src={user.avatar_url} alt="" />
              ) : (
                initials(user)
              )}
            </Link>
          </header>

          {!user.phone_verified_at && (
            <div className="verification-banner">
              <span>
                <strong>Téléphone non vérifié.</strong> Vérifiez votre numéro avant
                d’envoyer une demande.
              </span>
              <Link href="/client/profil">Vérifier maintenant</Link>
            </div>
          )}

          <div className="client-content">{children}</div>
        </div>

        <nav className="client-bottom-nav" aria-label="Navigation mobile">
          {NAVIGATION.slice(0, 4).map((item) => {
            const active = navIsActive(pathname, item.href);
            return (
              <Link
                className={active ? "bottom-nav-link active" : "bottom-nav-link"}
                href={item.href}
                key={item.href}
              >
                <span aria-hidden="true">{item.icon}</span>
                <small>{item.label === "Nouvelle demande" ? "Nouvelle" : item.label}</small>
              </Link>
            );
          })}
        </nav>
      </div>
    </ClientSessionContext.Provider>
  );
}
