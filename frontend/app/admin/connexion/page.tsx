"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { apiGet, apiMutation, getCsrfToken, type PublicUser } from "@/lib/client-api";
import type { AdminOverview } from "@/lib/admin-api";
import { sendJsonMutation } from "@/lib/safe-api";

export default function AdminLoginPage() {
  const router = useRouter();
  const [phone, setPhone] = useState("+223");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");

    try {
      const csrfToken = await getCsrfToken();
      await sendJsonMutation<PublicUser>("/api/v1/auth/login/", "POST", {
        csrfToken,
        body: { phone: phone.trim(), password },
      });

      try {
        await apiGet<AdminOverview>("/api/v1/admin/overview/");
      } catch (caught) {
        try {
          await apiMutation<void>("/api/v1/auth/logout/", "POST", {});
        } catch {
          // La connexion sera refusée visuellement ci-dessous.
        }
        throw caught;
      }

      router.replace("/admin");
      router.refresh();
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Connexion administrateur impossible.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="admin-auth-page">
      <section className="admin-auth-hero">
        <div className="admin-brand auth-brand">
          <span className="brand-mark" aria-hidden="true">B</span>
          <span>
            <strong>BKO Services</strong>
            <small>Administration</small>
          </span>
        </div>
        <div>
          <p className="eyebrow">Accès réservé</p>
          <h1>Superviser la plateforme sans contourner les permissions.</h1>
          <p className="intro">
            Les sections visibles dépendent des droits attribués au compte.
            Les opérations sensibles restent validées côté Django.
          </p>
        </div>
        <div className="auth-benefits">
          <span>✓ Permissions Django appliquées côté API</span>
          <span>✓ Actions sensibles auditées</span>
          <span>✓ Données privées affichées seulement si nécessaires</span>
        </div>
      </section>

      <section className="admin-auth-form-panel">
        <div className="auth-form-wrap">
          <p className="auth-kicker">Administration</p>
          <h2>Connexion</h2>
          <p className="auth-help">
            Utilisez un compte administrateur actif et habilité.
          </p>

          <form className="auth-form" onSubmit={submit}>
            <label className="field">
              <span>Numéro de téléphone</span>
              <input
                autoComplete="tel"
                inputMode="tel"
                maxLength={16}
                required
                value={phone}
                onChange={(event) => setPhone(event.target.value)}
              />
            </label>
            <label className="field">
              <span>Mot de passe</span>
              <input
                autoComplete="current-password"
                minLength={8}
                required
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>

            {error && <p className="form-error" role="alert">{error}</p>}

            <button className="button-primary button-wide" disabled={busy} type="submit">
              {busy ? "Vérification…" : "Accéder à l’administration"}
            </button>
          </form>

          <p className="provider-login-help">
            L’administration métier est distincte du Django Admin technique.
          </p>
          <Link className="text-link" href="/">
            Retour à l’accueil
          </Link>
        </div>
      </section>
    </main>
  );
}
