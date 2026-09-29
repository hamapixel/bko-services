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
  const [showPassword, setShowPassword] = useState(false);
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
    <main className="login-shell login-shell-admin">
      <section className="login-visual">
        <div className="login-brand">
          <span className="login-brand-mark" aria-hidden="true">B</span>
          <span>
            <strong>BKO Services</strong>
            <small>Administration</small>
          </span>
        </div>

        <div className="login-visual-copy">
          <span className="login-badge">Accès réservé</span>
          <h1>Pilotez BKO Services en toute sécurité.</h1>
          <p>
            Un espace clair pour superviser les prestataires, demandes,
            paiements et opérations sensibles.
          </p>
          <div className="login-points" aria-label="Sécurité administration">
            <span>Permissions contrôlées</span>
            <span>Actions auditées</span>
            <span>Données protégées</span>
          </div>
        </div>

        <p className="login-visual-foot">Console sécurisée · BKO Services</p>
      </section>

      <section className="login-card-zone">
        <div className="login-card login-card-admin">
          <div className="login-security-mark" aria-hidden="true">B</div>
          <div className="login-card-head">
            <span className="login-kicker">Administration</span>
            <h2>Connexion sécurisée</h2>
            <p>Utilisez votre compte administrateur autorisé.</p>
          </div>

          <form className="login-form" onSubmit={submit}>
            <label className="login-field">
              <span>Numéro de téléphone</span>
              <div className="login-input-wrap">
                <span className="login-input-icon" aria-hidden="true">Tél.</span>
                <input
                  className="login-input-with-prefix"
                  autoComplete="tel"
                  inputMode="tel"
                  maxLength={16}
                  required
                  placeholder="+223 70 00 00 00"
                  value={phone}
                  onChange={(event) => setPhone(event.target.value)}
                />
              </div>
            </label>

            <label className="login-field">
              <span>Mot de passe</span>
              <div className="login-input-wrap">
                <input
                  className="login-input-with-action"
                  autoComplete="current-password"
                  minLength={8}
                  required
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
                <button
                  className="login-input-action"
                  type="button"
                  onClick={() => setShowPassword((value) => !value)}
                >
                  {showPassword ? "Masquer" : "Afficher"}
                </button>
              </div>
            </label>

            {error && <p className="login-error" role="alert">{error}</p>}

            <button className="login-submit" disabled={busy} type="submit">
              {busy ? "Vérification…" : "Accéder à l’administration"}
            </button>
          </form>

          <div className="login-links">
            <p>Accès réservé aux comptes disposant des permissions requises.</p>
            <Link href="/">Retour à l’accueil</Link>
          </div>
        </div>
      </section>
    </main>
  );
}
