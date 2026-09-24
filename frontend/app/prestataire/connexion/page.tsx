"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { apiMutation, getCsrfToken, type PublicUser } from "@/lib/client-api";
import { sendJsonMutation } from "@/lib/safe-api";

function messageFromError(error: unknown) {
  return error instanceof Error
    ? error.message
    : "Une erreur inattendue est survenue.";
}

export default function ProviderLoginPage() {
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
      const user = await sendJsonMutation<PublicUser>(
        "/api/v1/auth/login/",
        "POST",
        {
          csrfToken,
          body: { phone: phone.trim(), password },
        },
      );

      if (user.role !== "PROVIDER") {
        try {
          await apiMutation<void>("/api/v1/auth/logout/", "POST", {});
        } catch {
          // La page affiche l'erreur de rôle ci-dessous.
        }
        throw new Error("Ce compte n’est pas un compte prestataire.");
      }

      router.replace("/prestataire");
      router.refresh();
    } catch (caught) {
      setError(messageFromError(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-shell login-shell-provider">
      <section className="login-visual">
        <div className="login-brand">
          <span className="login-brand-mark" aria-hidden="true">B</span>
          <span>
            <strong>BKO Services</strong>
            <small>Prestataires</small>
          </span>
        </div>

        <div className="login-visual-copy">
          <span className="login-badge">Espace professionnel</span>
          <h1>Vos interventions, au même endroit.</h1>
          <p>
            Consultez vos offres, gérez votre disponibilité et suivez chaque
            intervention simplement.
          </p>
          <div className="login-points" aria-label="Avantages prestataire">
            <span>Offres ciblées</span>
            <span>Suivi des interventions</span>
            <span>Accès sécurisé</span>
          </div>
        </div>

        <p className="login-visual-foot">BKO Services · Réseau prestataires</p>
      </section>

      <section className="login-card-zone">
        <div className="login-card">
          <div className="login-card-head">
            <span className="login-kicker">Prestataire vérifié</span>
            <h2>Connexion</h2>
            <p>Accédez à votre espace professionnel BKO Services.</p>
          </div>

          <form className="login-form" onSubmit={submit}>
            <label className="login-field">
              <span>Numéro de téléphone</span>
              <div className="login-input-wrap">
                <span className="login-input-icon" aria-hidden="true">+223</span>
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
              {busy ? "Connexion…" : "Se connecter"}
            </button>
          </form>

          <div className="login-links">
            <p>Pas encore prestataire ? Votre profil doit être validé par BKO Services.</p>
            <Link href="/connexion">Retour à l’espace client</Link>
          </div>
        </div>
      </section>
    </main>
  );
}
