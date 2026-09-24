"use client";

import Link from "next/link";

import { useAdminSession } from "@/components/admin/admin-shell";

export default function AdminDashboardPage() {
  const { overview } = useAdminSession();

  const cards = [
    ["Utilisateurs", overview.users_total, "Comptes enregistrés", "/admin/utilisateurs", overview.capabilities.users],
    ["Prestataires à valider", overview.providers_pending, "Dossiers en attente", "/admin/prestataires", overview.capabilities.providers],
    ["Demandes actives", overview.requests_active, "Parcours non terminés", "/admin/demandes", overview.capabilities.requests],
    ["Plaintes ouvertes", overview.complaints_open, "Ouvertes ou en examen", "/admin/plaintes", overview.capabilities.complaints],
    ["Paiements en attente", overview.payments_pending, "Transactions non terminales", "/admin/paiements", overview.capabilities.payments],
    ["Paiements à finaliser", overview.payments_unfulfilled, "Payés mais non appliqués", "/admin/paiements", overview.capabilities.payments],
    ["Abonnements actifs", overview.subscriptions_effective, "Droits effectifs aujourd’hui", "/admin/abonnements", overview.capabilities.subscriptions],
    ["Prestataires vérifiés", overview.providers_verified, "Profils actuellement vérifiés", "/admin/prestataires", overview.capabilities.providers],
  ] as const;

  return (
    <main>
      <section className="admin-page-head">
        <div>
          <p className="page-kicker">Vue d’ensemble</p>
          <h1>Tableau de bord administration</h1>
          <p>
            Les chiffres sont calculés côté serveur. Les sections accessibles
            dépendent des permissions du compte connecté.
          </p>
        </div>
      </section>

      <section className="admin-metric-grid">
        {cards
          .filter((card) => card[4])
          .map(([label, value, help, href]) => (
            <Link className="admin-metric-card" href={href} key={label}>
              <span>{label}</span>
              <strong>{value}</strong>
              <small>{help}</small>
            </Link>
          ))}
      </section>

      <section className="admin-security-callout">
        <strong>Principe de moindre privilège</strong>
        <p>
          Un administrateur ne voit pas automatiquement toutes les sections.
          Les utilisateurs, paiements, abonnements, prestataires et demandes
          restent soumis aux permissions Django configurées côté serveur.
        </p>
      </section>
    </main>
  );
}
