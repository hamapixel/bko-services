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
    <main className="provider-auth-page">
      <section className="provider-auth-hero">
        <div className="provider-brand auth-brand">
          <span className="brand-mark" aria-hidden="true">B</span>
          <span>
            <strong>BKO Services</strong>
            <small>Prestataires</small>
          </span>
        </div>
        <div>
          <p className="eyebrow">Espace professionnel</p>
          <h1>Recevez, acceptez, intervenez.</h1>
          <p className="intro">
            Consultez vos offres, gérez votre disponibilité et faites avancer
            chaque intervention selon le workflow sécurisé BKO Services.
          </p>
        </div>
        <div className="auth-benefits">
          <span>✓ Offres ciblées selon métier et zone</span>
          <span>✓ Adresse privée seulement après attribution</span>
          <span>✓ Abonnement et paiements suivis côté serveur</span>
        </div>
      </section>

      <section className="provider-auth-form-panel">
        <div className="auth-form-wrap">
          <p className="auth-kicker">Prestataire vérifié</p>
          <h2>Connexion</h2>
          <p className="auth-help">
            Utilisez le numéro associé à votre compte prestataire validé.
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
              {busy ? "Connexion…" : "Se connecter"}
            </button>
          </form>

          <p className="provider-login-help">
            Pas encore prestataire ? La candidature part d’un compte client
            vérifié puis doit être approuvée par l’administration.
          </p>
          <Link className="text-link" href="/connexion">
            Retour à l’espace client
          </Link>
        </div>
      </section>
    </main>
  );
}
