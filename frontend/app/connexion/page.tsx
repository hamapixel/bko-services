"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import {
  apiMutation,
  getCsrfToken,
  type PublicUser,
} from "@/lib/client-api";
import { sendJsonMutation } from "@/lib/safe-api";

type Mode = "login" | "register";

function messageFromError(error: unknown) {
  return error instanceof Error
    ? error.message
    : "Une erreur inattendue est survenue.";
}

export default function ConnexionPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("login");
  const [phone, setPhone] = useState("+223");
  const [password, setPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function finishLogin(user: PublicUser) {
    if (user.role !== "CLIENT") {
      try {
        await apiMutation<void>("/api/v1/auth/logout/", "POST", {});
      } catch {
        // The user will still see a clear role error below.
      }
      throw new Error("Ce compte n’est pas un compte client.");
    }

    router.replace("/client");
    router.refresh();
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");

    try {
      const csrfToken = await getCsrfToken();

      if (mode === "register") {
        await sendJsonMutation<PublicUser>("/api/v1/auth/register/", "POST", {
          csrfToken,
          body: {
            phone: phone.trim(),
            password,
            first_name: firstName.trim(),
            last_name: lastName.trim(),
            email: email.trim(),
          },
        });
      }

      const loginCsrf = mode === "register" ? await getCsrfToken() : csrfToken;
      const user = await sendJsonMutation<PublicUser>(
        "/api/v1/auth/login/",
        "POST",
        {
          csrfToken: loginCsrf,
          body: { phone: phone.trim(), password },
        },
      );
      await finishLogin(user);
    } catch (caught) {
      setError(messageFromError(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-panel auth-hero">
        <div className="client-brand auth-brand">
          <span className="brand-mark" aria-hidden="true">B</span>
          <span>
            <strong>BKO Services</strong>
            <small>Bamako</small>
          </span>
        </div>
        <div>
          <p className="eyebrow">Services de proximité</p>
          <h1>Votre professionnel, sans complication.</h1>
          <p className="intro">
            Créez une demande, suivez l’arrivée du prestataire et confirmez la
            fin de l’intervention depuis votre téléphone.
          </p>
        </div>
        <div className="auth-benefits">
          <span>✓ Professionnels vérifiés</span>
          <span>✓ Suivi clair de l’intervention</span>
          <span>✓ Brouillons disponibles hors connexion</span>
        </div>
      </section>

      <section className="auth-panel auth-form-panel">
        <div className="auth-form-wrap">
          <p className="auth-kicker">Espace client</p>
          <h2>{mode === "login" ? "Bon retour 👋" : "Créer mon compte"}</h2>
          <p className="auth-help">
            {mode === "login"
              ? "Connectez-vous avec votre numéro de téléphone."
              : "Votre compte sera créé avec le rôle Client uniquement."}
          </p>

          <div className="auth-tabs" role="tablist">
            <button
              className={mode === "login" ? "active" : ""}
              type="button"
              onClick={() => {
                setMode("login");
                setError("");
              }}
            >
              Connexion
            </button>
            <button
              className={mode === "register" ? "active" : ""}
              type="button"
              onClick={() => {
                setMode("register");
                setError("");
              }}
            >
              Inscription
            </button>
          </div>

          <form className="auth-form" onSubmit={submit}>
            {mode === "register" && (
              <div className="form-grid two">
                <label className="field">
                  <span>Prénom</span>
                  <input
                    autoComplete="given-name"
                    maxLength={150}
                    value={firstName}
                    onChange={(event) => setFirstName(event.target.value)}
                  />
                </label>
                <label className="field">
                  <span>Nom</span>
                  <input
                    autoComplete="family-name"
                    maxLength={150}
                    value={lastName}
                    onChange={(event) => setLastName(event.target.value)}
                  />
                </label>
              </div>
            )}

            <label className="field">
              <span>Numéro de téléphone</span>
              <input
                autoComplete="tel"
                inputMode="tel"
                required
                maxLength={16}
                placeholder="+22370000000"
                value={phone}
                onChange={(event) => setPhone(event.target.value)}
              />
            </label>

            {mode === "register" && (
              <label className="field">
                <span>E-mail (facultatif)</span>
                <input
                  autoComplete="email"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </label>
            )}

            <label className="field">
              <span>Mot de passe</span>
              <input
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                minLength={8}
                required
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
              {mode === "register" && (
                <small>Utilisez un mot de passe long et difficile à deviner.</small>
              )}
            </label>

            {error && <p className="form-error" role="alert">{error}</p>}

            <button className="button-primary button-wide" disabled={busy} type="submit">
              {busy
                ? "Traitement…"
                : mode === "login"
                  ? "Se connecter"
                  : "Créer le compte"}
            </button>
          </form>
        </div>
      </section>
    </main>
  );
}
