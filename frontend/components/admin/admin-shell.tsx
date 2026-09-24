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
import type { AdminOverview } from "@/lib/admin-api";

type AdminSessionValue = {
  user: PublicUser;
  overview: AdminOverview;
  refreshOverview: () => Promise<void>;
  refreshUser: () => Promise<void>;
};

const AdminSessionContext = createContext<AdminSessionValue | null>(null);

const NAV_ITEMS = [
  { href: "/admin", label: "Accueil", icon: "⌂", capability: null },
  { href: "/admin/prestataires", label: "Prestataires", icon: "✓", capability: "providers" },
  { href: "/admin/demandes", label: "Demandes", icon: "≡", capability: "requests" },
  { href: "/admin/plaintes", label: "Plaintes", icon: "!", capability: "complaints" },
  { href: "/admin/abonnements", label: "Abonnements", icon: "◇", capability: "subscriptions" },
  { href: "/admin/paiements", label: "Paiements", icon: "₣", capability: "payments" },
  { href: "/admin/utilisateurs", label: "Utilisateurs", icon: "●", capability: "users" },
  { href: "/admin/profil", label: "Mon profil", icon: "◉", capability: null },
] as const;

export function useAdminSession() {
  const value = useContext(AdminSessionContext);
  if (!value) {
    throw new Error("useAdminSession doit être utilisé dans AdminShell.");
  }
  return value;
}

function navIsActive(pathname: string, href: string) {
  if (href === "/admin") return pathname === href;
  return pathname.startsWith(href);
}

function initials(user: PublicUser) {
  const name = [user.first_name, user.last_name].filter(Boolean).join(" ").trim();
  const source = name || user.phone;
  return source
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join("");
}

export default function AdminShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const isLoginPage = pathname === "/admin/connexion";
  const [user, setUser] = useState<PublicUser | null>(null);
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [loading, setLoading] = useState(!isLoginPage);
  const [menuOpen, setMenuOpen] = useState(false);
  const [error, setError] = useState("");

  const refreshOverview = useCallback(async () => {
    const next = await apiGet<AdminOverview>("/api/v1/admin/overview/");
    setOverview(next);
  }, []);

  const refreshUser = useCallback(async () => {
    const next = await apiGet<PublicUser>("/api/v1/auth/me/");
    setUser(next);
  }, []);

  useEffect(() => {
    if (isLoginPage) return;

    let active = true;
    Promise.all([
      apiGet<PublicUser>("/api/v1/auth/me/"),
      apiGet<AdminOverview>("/api/v1/admin/overview/"),
    ])
      .then(([account, adminOverview]) => {
        if (!active) return;
        setUser(account);
        setOverview(adminOverview);
        setError("");
      })
      .catch((caught: unknown) => {
        if (!active) return;
        if (
          caught instanceof ApiReadError &&
          (caught.status === 401 || caught.status === 403)
        ) {
          router.replace("/admin/connexion");
          return;
        }
        setError(
          caught instanceof Error
            ? caught.message
            : "Impossible de charger l’espace administration.",
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
      user && overview
        ? {
            user,
            overview,
            refreshOverview,
            refreshUser,
          }
        : null,
    [overview, refreshOverview, refreshUser, user],
  );

  async function logout() {
    try {
      await apiMutation<void>("/api/v1/auth/logout/", "POST", {});
    } finally {
      router.replace("/admin/connexion");
      router.refresh();
    }
  }

  if (isLoginPage) {
    return <>{children}</>;
  }

  if (loading) {
    return (
      <main className="admin-loading">
        <div className="loading-spinner" aria-hidden="true" />
        <p>Chargement de l’administration…</p>
      </main>
    );
  }

  if (error) {
    return (
      <main className="admin-loading">
        <section className="empty-state">
          <strong>Administration indisponible</strong>
          <p>{error}</p>
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

  if (!user || !overview || !contextValue) return null;

  const visibleItems = NAV_ITEMS.filter((item) => {
    if (!item.capability) return true;
    return overview.capabilities[item.capability];
  });

  return (
    <AdminSessionContext.Provider value={contextValue}>
      <div className="admin-app">
        <aside className={`admin-sidebar ${menuOpen ? "is-open" : ""}`}>
          <div className="admin-sidebar-head">
            <Link className="admin-brand" href="/admin">
              <span className="brand-mark" aria-hidden="true">B</span>
              <span>
                <strong>BKO Services</strong>
                <small>Administration</small>
              </span>
            </Link>
            <button
              className="icon-button admin-mobile-only"
              type="button"
              aria-label="Fermer le menu"
              onClick={() => setMenuOpen(false)}
            >
              ×
            </button>
          </div>

          <nav className="admin-nav" aria-label="Navigation administration">
            {visibleItems.map((item) => (
              <Link
                className={
                  navIsActive(pathname, item.href)
                    ? "admin-nav-link active"
                    : "admin-nav-link"
                }
                href={item.href}
                key={item.href}
                onClick={() => setMenuOpen(false)}
              >
                <span className="admin-nav-icon" aria-hidden="true">{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            ))}
          </nav>

          <div className="admin-account-card">
            <span className="admin-avatar">
              {user.has_avatar && user.avatar_url ? (
                <img src={user.avatar_url} alt="" />
              ) : (
                initials(user)
              )}
            </span>
            <span className="admin-account-copy">
              <strong>
                {[user.first_name, user.last_name].filter(Boolean).join(" ") ||
                  user.role}
              </strong>
              <small>{user.phone}</small>
            </span>
            <button className="text-button" type="button" onClick={logout}>
              Quitter
            </button>
          </div>
        </aside>

        {menuOpen && (
          <button
            className="admin-menu-backdrop"
            type="button"
            aria-label="Fermer le menu"
            onClick={() => setMenuOpen(false)}
          />
        )}

        <div className="admin-main">
          <header className="admin-topbar">
            <button
              className="icon-button admin-mobile-only"
              type="button"
              aria-label="Ouvrir le menu"
              onClick={() => setMenuOpen(true)}
            >
              ☰
            </button>
            <div className="admin-topbar-title">
              <strong>Administration BKO Services</strong>
              <small>Supervision et opérations habilitées.</small>
            </div>
            <span className="admin-role-badge">{user.role}</span>
            <Link className="admin-topbar-avatar" href="/admin/profil" aria-label="Ouvrir mon profil">
              {user.has_avatar && user.avatar_url ? (
                <img src={user.avatar_url} alt="" />
              ) : (
                initials(user)
              )}
            </Link>
          </header>

          <div className="admin-content">{children}</div>
        </div>

        <nav className="admin-bottom-nav" aria-label="Navigation mobile">
          {visibleItems.slice(0, 4).map((item) => (
            <Link
              className={
                navIsActive(pathname, item.href)
                  ? "admin-bottom-link active"
                  : "admin-bottom-link"
              }
              href={item.href}
              key={item.href}
            >
              <span aria-hidden="true">{item.icon}</span>
              <small>{item.label}</small>
            </Link>
          ))}
        </nav>
      </div>
    </AdminSessionContext.Provider>
  );
}
