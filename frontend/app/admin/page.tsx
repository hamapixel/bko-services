"use client";

import Link from "next/link";

import { useAdminSession } from "@/components/admin/admin-shell";

export default function AdminDashboardPage() {
  const { overview, user } = useAdminSession();

  const cards = [
    ["Utilisateurs", overview.users_total, "Comptes enregistrés", "/admin/utilisateurs", overview.capabilities.users, "●"],
    ["Prestataires à valider", overview.providers_pending, "Dossiers en attente", "/admin/prestataires", overview.capabilities.providers, "✓"],
    ["Demandes actives", overview.requests_active, "Parcours non terminés", "/admin/demandes", overview.capabilities.requests, "≡"],
    ["Plaintes ouvertes", overview.complaints_open, "Ouvertes ou en examen", "/admin/plaintes", overview.capabilities.complaints, "!"],
    ["Paiements en attente", overview.payments_pending, "Transactions non terminales", "/admin/paiements", overview.capabilities.payments, "₣"],
    ["Paiements à finaliser", overview.payments_unfulfilled, "Payés mais non appliqués", "/admin/paiements", overview.capabilities.payments, "↻"],
    ["Abonnements actifs", overview.subscriptions_effective, "Droits effectifs aujourd’hui", "/admin/abonnements", overview.capabilities.subscriptions, "◇"],
    ["Prestataires vérifiés", overview.providers_verified, "Profils actuellement vérifiés", "/admin/prestataires", overview.capabilities.providers, "★"],
  ] as const;

  const displayName =
    [user.first_name, user.last_name].filter(Boolean).join(" ") || "Administrateur";

  return (
    <main className="admin-dashboard-premium">
      <section className="role-welcome-card admin-welcome-card">
        <div className="role-welcome-copy">
          <span className="role-welcome-kicker">Console sécurisée</span>
          <h1>Bonjour {displayName} 👋</h1>
          <p>
            Supervisez BKO Services depuis une vue claire, avec des accès qui
            restent limités aux permissions de votre compte.
          </p>
          <div className="role-welcome-actions">
            {overview.capabilities.providers && (
              <Link className="role-primary-action" href="/admin/prestataires">
                Prestataires à contrôler
              </Link>
            )}
            <Link className="role-secondary-action" href="/admin/profil">
              Mon profil
            </Link>
          </div>
        </div>

        <div className="admin-welcome-visual" aria-hidden="true">
          <div className="admin-command-center">
            <span>B</span>
            <strong>BKO Admin</strong>
            <small>{user.role}</small>
          </div>
          <span className="admin-command-orb admin-command-orb-one">✓</span>
          <span className="admin-command-orb admin-command-orb-two">₣</span>
          <span className="admin-command-orb admin-command-orb-three">≡</span>
        </div>
      </section>

      <section className="admin-premium-metric-grid">
        {cards
          .filter((card) => card[4])
          .map(([label, value, help, href, , icon]) => (
            <Link className="admin-premium-metric-card" href={href} key={label}>
              <span className="admin-premium-metric-icon">{icon}</span>
              <div>
                <small>{label}</small>
                <strong>{value}</strong>
                <span>{help}</span>
              </div>
            </Link>
          ))}
      </section>

      <section className="admin-security-callout admin-security-premium">
        <span className="admin-security-icon" aria-hidden="true">✓</span>
        <div>
          <strong>Sécurité par permissions</strong>
          <p>
            Les actions sensibles restent contrôlées par Django côté serveur.
            Une page visible ne donne jamais automatiquement un droit d’action.
          </p>
        </div>
      </section>
    </main>
  );
}
