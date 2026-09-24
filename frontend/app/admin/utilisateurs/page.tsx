"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import {
  apiGet,
  formatDate,
  type AdminUser,
  type ApiPage,
} from "@/lib/admin-api";

type RoleFilter = "ALL" | AdminUser["role"];

function normalizeNext(next: string | null) {
  if (!next) return null;
  const parsed = new URL(next, window.location.origin);
  return `${parsed.pathname}${parsed.search}`;
}

export default function AdminUsersPage() {
  const [items, setItems] = useState<AdminUser[]>([]);
  const [role, setRole] = useState<RoleFilter>("ALL");
  const [active, setActive] = useState<"" | "true" | "false">("");
  const [query, setQuery] = useState("");
  const [nextPage, setNextPage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");

  async function load(
    selectedRole = role,
    selectedActive = active,
    search = query,
  ) {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      if (selectedRole !== "ALL") params.set("role", selectedRole);
      if (selectedActive) params.set("active", selectedActive);
      if (search.trim()) params.set("q", search.trim());
      const suffix = params.toString() ? `?${params.toString()}` : "";
      const page = await apiGet<ApiPage<AdminUser>>(
        `/api/v1/admin/users/${suffix}`,
      );
      setItems(page.results);
      setNextPage(normalizeNext(page.next));
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Impossible de charger les utilisateurs.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let mounted = true;
    apiGet<ApiPage<AdminUser>>("/api/v1/admin/users/")
      .then((page) => {
        if (!mounted) return;
        setItems(page.results);
        setNextPage(normalizeNext(page.next));
      })
      .catch((caught) => {
        if (!mounted) return;
        setError(
          caught instanceof Error
            ? caught.message
            : "Impossible de charger les utilisateurs.",
        );
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  async function loadMore() {
    if (!nextPage) return;
    setLoadingMore(true);
    try {
      const page = await apiGet<ApiPage<AdminUser>>(nextPage);
      setItems((current) => [...current, ...page.results]);
      setNextPage(normalizeNext(page.next));
    } finally {
      setLoadingMore(false);
    }
  }

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void load(role, active, query);
  }

  return (
    <main>
      <section className="admin-page-head">
        <div>
          <p className="page-kicker">Utilisateurs</p>
          <h1>Supervision des comptes</h1>
          <p>
            Cette vue est en lecture seule : aucun mot de passe, changement de rôle
            ou permission n’est modifiable depuis cet écran.
          </p>
        </div>
      </section>

      <form className="admin-search-row" onSubmit={submitSearch}>
        <input
          aria-label="Rechercher un utilisateur"
          placeholder="Téléphone, nom ou e-mail"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <button className="button-secondary" type="submit">Rechercher</button>
      </form>

      <div className="admin-filter-bar">
        <select
          aria-label="Filtrer par rôle"
          value={role}
          onChange={(event) => {
            const next = event.target.value as RoleFilter;
            setRole(next);
            void load(next, active, query);
          }}
        >
          <option value="ALL">Tous les rôles</option>
          <option value="CLIENT">Clients</option>
          <option value="PROVIDER">Prestataires</option>
          <option value="ADMIN">Administrateurs</option>
          <option value="SUPERADMIN">Super administrateurs</option>
        </select>

        <select
          aria-label="Filtrer par état"
          value={active}
          onChange={(event) => {
            const next = event.target.value as "" | "true" | "false";
            setActive(next);
            void load(role, next, query);
          }}
        >
          <option value="">Tous les états</option>
          <option value="true">Actifs</option>
          <option value="false">Inactifs</option>
        </select>
      </div>

      {loading && <div className="skeleton-list">Chargement…</div>}
      {error && <div className="inline-error">{error}</div>}

      {!loading && !error && items.length === 0 && (
        <div className="empty-state">
          <strong>Aucun utilisateur</strong>
          <p>Aucun compte ne correspond aux filtres.</p>
        </div>
      )}

      <div className="admin-list">
        {items.map((user) => (
          <Link
            className="admin-list-card"
            href={`/admin/utilisateurs/${user.id}`}
            key={user.id}
          >
            <div>
              <span className="request-meta">{user.role}</span>
              <h3>
                {[user.first_name, user.last_name].filter(Boolean).join(" ") ||
                  user.phone}
              </h3>
              <p>{user.phone}{user.email ? ` · ${user.email}` : ""}</p>
            </div>
            <div className="admin-list-meta">
              <span className={user.is_active ? "status-badge success" : "status-badge danger"}>
                {user.is_active ? "Actif" : "Inactif"}
              </span>
              <small>
                Téléphone {user.phone_verified_at ? "vérifié" : "non vérifié"}
              </small>
              <small>{formatDate(user.date_joined)}</small>
            </div>
          </Link>
        ))}
      </div>

      {nextPage && !loading && (
        <div className="load-more-row">
          <button
            className="button-secondary"
            disabled={loadingMore}
            type="button"
            onClick={loadMore}
          >
            {loadingMore ? "Chargement…" : "Charger plus"}
          </button>
        </div>
      )}
    </main>
  );
}
