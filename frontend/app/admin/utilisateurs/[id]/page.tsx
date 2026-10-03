"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useAdminSession } from "@/components/admin/admin-shell";
import { useBkoAlert } from "@/components/bko-alert";
import {
  apiGet,
  apiMutation,
  formatDate,
  type AdminUser,
} from "@/lib/admin-api";

export default function AdminUserDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { user: actor } = useAdminSession();
  const alerts = useBkoAlert();
  const [user, setUser] = useState<AdminUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
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

  async function setAccountActive(nextActive: boolean) {
    if (!user || busy) return;
    const confirmed = await alerts.confirmAction({
      title: nextActive ? "Réactiver ce compte ?" : "Désactiver ce compte ?",
      message: nextActive
        ? `${user.phone} pourra de nouveau se connecter à BKO Services.`
        : `${user.phone} ne pourra plus se connecter. Son historique sera conservé.`,
      confirmLabel: nextActive ? "Réactiver" : "Désactiver",
      danger: !nextActive,
    });
    if (!confirmed) return;

    setBusy(true);
    setError("");
    try {
      const updated = await apiMutation<AdminUser>(
        `/api/v1/admin/users/${user.id}/status/`,
        "PATCH",
        { is_active: nextActive },
      );
      setUser(updated);
      alerts.success({
        title: nextActive ? "Compte réactivé" : "Compte désactivé",
        message: nextActive
          ? "Le serveur a réactivé le compte avec succès."
          : "Le serveur a bloqué la connexion tout en conservant l’historique.",
      });
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Action impossible.";
      setError(message);
      alerts.error({ title: "Action refusée", message });
    } finally {
      setBusy(false);
    }
  }

  async function deleteAccount() {
    if (!user || busy) return;
    const confirmed = await alerts.confirmAction({
      title: "Supprimer définitivement ce compte ?",
      message: `${user.phone} sera supprimé uniquement si le serveur confirme qu’aucun historique BKO Services n’est lié à ce compte.`,
      confirmLabel: "Supprimer définitivement",
      danger: true,
    });
    if (!confirmed) return;

    setBusy(true);
    setError("");
    try {
      await apiMutation<void>(`/api/v1/admin/users/${user.id}/delete/`, "DELETE");
      alerts.success({
        title: "Compte supprimé",
        message: "Le serveur a confirmé la suppression du compte.",
      });
      router.replace("/admin/utilisateurs");
      router.refresh();
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Suppression impossible.";
      setError(message);
      alerts.error({ title: "Suppression refusée", message });
      setBusy(false);
    }
  }

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

  const canManage =
    actor.role === "SUPERADMIN" &&
    actor.id !== user.id &&
    user.role !== "SUPERADMIN";

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

      {error && <div className="shell-logout-error" role="alert">{error}</div>}

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
            <strong>Gestion sécurisée</strong>
            <p>
              Un numéro correspond à un seul compte et un seul rôle actif. La
              désactivation bloque la connexion sans supprimer l’historique.
            </p>
          </section>

          {canManage && (
            <section className="detail-card">
              <h2>Actions du compte</h2>
              <p>
                Privilégiez la désactivation pour conserver l’historique des
                demandes, interventions, paiements et abonnements.
              </p>
              <div className="role-welcome-actions" style={{ marginTop: 16 }}>
                {user.is_active ? (
                  <button
                    className="button-secondary"
                    type="button"
                    disabled={busy}
                    onClick={() => void setAccountActive(false)}
                  >
                    Désactiver
                  </button>
                ) : (
                  <button
                    className="button-primary"
                    type="button"
                    disabled={busy}
                    onClick={() => void setAccountActive(true)}
                  >
                    Réactiver
                  </button>
                )}
                <button
                  className="button-secondary"
                  type="button"
                  disabled={busy}
                  onClick={() => void deleteAccount()}
                  style={{ color: "#b42318" }}
                >
                  Supprimer si aucun historique
                </button>
              </div>
            </section>
          )}
        </aside>
      </div>
    </main>
  );
}
