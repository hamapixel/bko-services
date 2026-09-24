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
import type { ProviderProfile } from "@/lib/provider-api";

type ProviderSessionValue = {
  user: PublicUser;
  profile: ProviderProfile;
  refreshProfile: () => Promise<void>;
};

const ProviderSessionContext = createContext<ProviderSessionValue | null>(null);

const NAVIGATION = [
  { href: "/prestataire", label: "Accueil", icon: "⌂" },
  { href: "/prestataire/offres", label: "Offres", icon: "✦" },
  { href: "/prestataire/interventions", label: "Interventions", icon: "≡" },
  { href: "/prestataire/abonnement", label: "Abonnement", icon: "◇" },
  { href: "/prestataire/avis", label: "Avis", icon: "★" },
  { href: "/prestataire/profil", label: "Profil", icon: "●" },
];

export function useProviderSession() {
  const context = useContext(ProviderSessionContext);
  if (!context) {
    throw new Error("useProviderSession doit être utilisé dans ProviderShell.");
  }
  return context;
}

function navIsActive(pathname: string, href: string) {
  if (href === "/prestataire") return pathname === href;
  if (href === "/prestataire/interventions") {
    return pathname.startsWith("/prestataire/interventions");
  }
  return pathname.startsWith(href);
}

function initials(profile: ProviderProfile) {
  return profile.display_name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join("");
}

export default function ProviderShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const isLoginPage = pathname === "/prestataire/connexion";
  const [user, setUser] = useState<PublicUser | null>(null);
  const [profile, setProfile] = useState<ProviderProfile | null>(null);
  const [loading, setLoading] = useState(!isLoginPage);
  const [menuOpen, setMenuOpen] = useState(false);
  const [sessionError, setSessionError] = useState("");

  const refreshProfile = useCallback(async () => {
    const next = await apiGet<ProviderProfile>("/api/v1/providers/application/");
    setProfile(next);
  }, []);

  useEffect(() => {
    if (isLoginPage) {
      return;
    }

    let active = true;

    Promise.all([
      apiGet<PublicUser>("/api/v1/auth/me/"),
      apiGet<ProviderProfile>("/api/v1/providers/application/"),
    ])
      .then(([account, provider]) => {
        if (!active) return;
        setUser(account);
        setProfile(provider);
        setSessionError("");
      })
      .catch((error: unknown) => {
        if (!active) return;
        if (
          error instanceof ApiReadError &&
          (error.status === 401 || error.status === 403 || error.status === 404)
        ) {
          router.replace("/prestataire/connexion");
          return;
        }
        setSessionError(
          error instanceof Error
            ? error.message
            : "Impossible de charger votre espace prestataire.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [isLoginPage, router]);

  const contextValue = useMemo(
    () =>
      user && profile
        ? {
            user,
            profile,
            refreshProfile,
          }
        : null,
    [profile, refreshProfile, user],
  );

  async function logout() {
    try {
      await apiMutation<void>("/api/v1/auth/logout/", "POST", {});
    } finally {
      router.replace("/prestataire/connexion");
      router.refresh();
    }
  }

  if (isLoginPage) {
    return <>{children}</>;
  }

  if (loading) {
    return (
      <main className="provider-loading">
        <div className="loading-spinner" aria-hidden="true" />
        <p>Chargement de votre espace prestataire…</p>
      </main>
    );
  }

  if (sessionError) {
    return (
      <main className="provider-loading">
        <section className="empty-state">
          <strong>Connexion au serveur impossible</strong>
          <p>{sessionError}</p>
          <button
            className="button-primary"
            type="button"
            onClick={() => window.location.reload()}
          >
            Réessayer
          </button>
        </section>
      </main>
    );
  }

  if (!user || !profile || !contextValue) return null;

  if (user.role !== "PROVIDER" || profile.status !== "VERIFIED") {
    return (
      <main className="provider-loading">
        <section className="empty-state">
          <strong>Espace réservé aux prestataires vérifiés</strong>
          <p>
            Rôle : {user.role} · dossier : {profile.status}.
          </p>
          <button className="button-primary" type="button" onClick={logout}>
            Se déconnecter
          </button>
        </section>
      </main>
    );
  }

  return (
    <ProviderSessionContext.Provider value={contextValue}>
      <div className="provider-app">
        <aside className={`provider-sidebar ${menuOpen ? "is-open" : ""}`}>
          <div className="provider-sidebar-head">
            <Link className="provider-brand" href="/prestataire">
              <span className="brand-mark" aria-hidden="true">B</span>
              <span>
                <strong>BKO Services</strong>
                <small>Espace prestataire</small>
              </span>
            </Link>
            <button
              className="icon-button provider-mobile-only"
              type="button"
              aria-label="Fermer le menu"
              onClick={() => setMenuOpen(false)}
            >
              ×
            </button>
          </div>

          <div className="provider-availability-state">
            <span
              className={
                profile.is_available
                  ? "availability-dot online"
                  : "availability-dot offline"
              }
            />
            <span>
              <strong>{profile.is_available ? "Disponible" : "Indisponible"}</strong>
              <small>
                {profile.is_available
                  ? "Vous pouvez recevoir de nouvelles offres."
                  : "Aucune nouvelle offre ne vous sera proposée."}
              </small>
            </span>
          </div>

          <nav className="provider-nav" aria-label="Navigation prestataire">
            {NAVIGATION.map((item) => {
              const active = navIsActive(pathname, item.href);
              return (
                <Link
                  className={active ? "provider-nav-link active" : "provider-nav-link"}
                  href={item.href}
                  key={item.href}
                  onClick={() => setMenuOpen(false)}
                >
                  <span className="provider-nav-icon" aria-hidden="true">{item.icon}</span>
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>

          <div className="provider-account-card">
            <span className="provider-avatar">{initials(profile)}</span>
            <span className="provider-account-copy">
              <strong>{profile.display_name}</strong>
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
            className="provider-menu-backdrop"
            type="button"
            aria-label="Fermer le menu"
            onClick={() => setMenuOpen(false)}
          />
        )}

        <div className="provider-main">
          <header className="provider-topbar">
            <button
              className="icon-button provider-mobile-only"
              type="button"
              aria-label="Ouvrir le menu"
              onClick={() => setMenuOpen(true)}
            >
              ☰
            </button>
            <div className="provider-topbar-title">
              <strong>{profile.display_name}</strong>
              <small>Gérez vos offres et interventions.</small>
            </div>
            <Link className="provider-mini-avatar" href="/prestataire/profil">
              {initials(profile)}
            </Link>
          </header>

          <div className="provider-content">{children}</div>
        </div>

        <nav className="provider-bottom-nav" aria-label="Navigation mobile">
          {NAVIGATION.slice(0, 4).map((item) => {
            const active = navIsActive(pathname, item.href);
            return (
              <Link
                className={active ? "provider-bottom-link active" : "provider-bottom-link"}
                href={item.href}
                key={item.href}
              >
                <span aria-hidden="true">{item.icon}</span>
                <small>{item.label}</small>
              </Link>
            );
          })}
        </nav>
      </div>
    </ProviderSessionContext.Provider>
  );
}
