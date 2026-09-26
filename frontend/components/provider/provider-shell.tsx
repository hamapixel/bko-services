"use client";
/* eslint-disable @next/next/no-img-element -- private authenticated avatar URLs intentionally bypass image optimization. */

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
  refreshUser: () => Promise<void>;
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
  const isPublicProviderPage =
    pathname === "/prestataire/connexion" ||
    pathname.startsWith("/prestataire/devenir");
  const [user, setUser] = useState<PublicUser | null>(null);
  const [profile, setProfile] = useState<ProviderProfile | null>(null);
  const [loading, setLoading] = useState(!isPublicProviderPage);
  const [menuOpen, setMenuOpen] = useState(false);
  const [sessionError, setSessionError] = useState("");
  const [logoutBusy, setLogoutBusy] = useState(false);
  const [logoutError, setLogoutError] = useState("");

  const refreshProfile = useCallback(async () => {
    const next = await apiGet<ProviderProfile>("/api/v1/providers/application/");
    setProfile(next);
  }, []);

  const refreshUser = useCallback(async () => {
    const next = await apiGet<PublicUser>("/api/v1/auth/me/");
    setUser(next);
  }, []);

  useEffect(() => {
    if (isPublicProviderPage) {
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
  }, [isPublicProviderPage, router]);

  const contextValue = useMemo(
    () =>
      user && profile
        ? {
            user,
            profile,
            refreshProfile,
            refreshUser,
          }
        : null,
    [profile, refreshProfile, refreshUser, user],
  );

  async function logout() {
    if (logoutBusy) return;
    setLogoutBusy(true);
    setLogoutError("");
    try {
      await apiMutation<void>("/api/v1/auth/logout/", "POST", {});
      setUser(null);
      setProfile(null);
      router.replace("/prestataire/connexion");
      router.refresh();
    } catch (caught) {
      setLogoutError(caught instanceof Error ? caught.message : "Déconnexion impossible. Réessayez.");
      setLogoutBusy(false);
    }
  }

  if (isPublicProviderPage) {
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
                  ? "Un abonnement actif est aussi nécessaire pour recevoir des offres."
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
            <span className="provider-avatar">
              {user.has_avatar && user.avatar_url ? (
                <img src={user.avatar_url} alt="" />
              ) : (
                initials(profile)
              )}
            </span>
            <span className="provider-account-copy">
              <strong>{profile.display_name}</strong>
              <small>{user.phone}</small>
            </span>
            <button
              className="text-button"
              type="button"
              onClick={logout}
              disabled={logoutBusy}
              aria-label="Se déconnecter"
            >
              Se déconnecter
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
            <button className="shell-logout-button" type="button" onClick={logout} disabled={logoutBusy} aria-label="Se déconnecter">
              <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/></svg>
              <span>Déconnexion</span>
            </button>
            <Link className="provider-mini-avatar" href="/prestataire/profil" aria-label="Ouvrir mon profil">
              {user.has_avatar && user.avatar_url ? (
                <img src={user.avatar_url} alt="" />
              ) : (
                initials(profile)
              )}
            </Link>
          </header>

          {logoutError && <div className="shell-logout-error" role="alert">{logoutError}</div>}

          <div className="provider-content">{children}</div>
        </div>

        <nav className="provider-bottom-nav" aria-label="Navigation mobile">
          {NAVIGATION.filter((item) => item.href !== "/prestataire/avis").map((item) => {
            const active = navIsActive(pathname, item.href);
            return (
              <Link
                className={active ? "provider-bottom-link active" : "provider-bottom-link"}
                href={item.href}
                key={item.href}
                aria-current={active ? "page" : undefined}
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
