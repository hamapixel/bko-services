"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import {
  apiGet,
  formatDate,
  type AdminUser,
} from "@/lib/admin-api";

export default function AdminUserDetailPage() {
  const params = useParams<{ id: string }>();
  const [user, setUser] = useState<AdminUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;
    apiGet<AdminUser>(`/api/v1/admin/users/${params.id}/`)
      .then((data) => {
        if (mounted) setUser(data);
      })
      .catch((caught) => {
        if (!mounted) return;
        setError(
          caught instanceof Error ? caught.message : "Utilisateur introuvable.",
        );
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [params.id]);

  if (loading) return <div className="skeleton-list">Chargement…</div>;

  if (!user) {
    return (
      <div className="empty-state">
        <strong>Utilisateur indisponible</strong>
        <p>{error}</p>
        <Link className="button-secondary" href="/admin/utilisateurs">
          Retour
        </Link>
      </div>
    );
  }

  return (
    <main>
      <section className="admin-page-head">
        <div>
          <Link className="back-link" href="/admin/utilisateurs">
            ← Utilisateurs
          </Link>
          <p className="page-kicker">{user.role}</p>
          <h1>
            {[user.first_name, user.last_name].filter(Boolean).join(" ") ||
              user.phone}
          </h1>
          <span className={user.is_active ? "status-badge success" : "status-badge danger"}>
            {user.is_active ? "Actif" : "Inactif"}
          </span>
        </div>
      </section>

      <div className="detail-grid">
        <section className="detail-card">
          <h2>Informations du compte</h2>
          <dl className="detail-list">
            <div><dt>Téléphone</dt><dd>{user.phone}</dd></div>
            <div><dt>E-mail</dt><dd>{user.email || "—"}</dd></div>
            <div><dt>Rôle</dt><dd>{user.role}</dd></div>
            <div><dt>Staff</dt><dd>{user.is_staff ? "Oui" : "Non"}</dd></div>
            <div>
              <dt>Téléphone vérifié</dt>
              <dd>{user.phone_verified_at ? formatDate(user.phone_verified_at) : "Non"}</dd>
            </div>
            <div><dt>Créé le</dt><dd>{formatDate(user.date_joined)}</dd></div>
            <div>
              <dt>Dernière connexion</dt>
              <dd>{user.last_login ? formatDate(user.last_login) : "—"}</dd>
            </div>
          </dl>
        </section>

        <aside className="detail-side">
          <section className="security-note">
            <strong>Lecture seule</strong>
            <p>
              Le rôle, le statut actif, les permissions et les mots de passe ne
              sont jamais modifiés depuis cette interface de supervision.
            </p>
          </section>
        </aside>
      </div>
    </main>
  );
}
