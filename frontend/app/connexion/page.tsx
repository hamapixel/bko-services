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
  const [showPassword, setShowPassword] = useState(false);
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
    <main className="login-shell login-shell-client">
      <section className="login-visual">
        <div className="login-brand">
          <span className="login-brand-mark" aria-hidden="true">B</span>
          <span>
            <strong>BKO Services</strong>
            <small>Bamako</small>
          </span>
        </div>

        <div className="login-visual-copy">
          <span className="login-badge">Services de proximité</span>
          <h1>Le bon professionnel, simplement.</h1>
          <p>
            Trouvez un prestataire vérifié et suivez votre intervention depuis
            votre téléphone.
          </p>
          <div className="login-points" aria-label="Avantages BKO Services">
            <span>Professionnels vérifiés</span>
            <span>Suivi en temps réel</span>
            <span>Simple et sécurisé</span>
          </div>
        </div>

        <p className="login-visual-foot">BKO Services · Bamako</p>
      </section>

      <section className="login-card-zone">
        <div className="login-card">
          <div className="login-card-head">
            <span className="login-kicker">Espace client</span>
            <h2>{mode === "login" ? "Bon retour" : "Créer mon compte"}</h2>
            <p>
              {mode === "login"
                ? "Connectez-vous pour accéder à vos demandes."
                : "Créez votre compte en quelques secondes."}
            </p>
          </div>

          <div className="login-tabs" role="tablist" aria-label="Authentification">
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

          <form className="login-form" onSubmit={submit}>
            {mode === "register" && (
              <div className="login-grid-two">
                <label className="login-field">
                  <span>Prénom</span>
                  <input
                    autoComplete="given-name"
                    maxLength={150}
                    placeholder="Votre prénom"
                    value={firstName}
                    onChange={(event) => setFirstName(event.target.value)}
                  />
                </label>
                <label className="login-field">
                  <span>Nom</span>
                  <input
                    autoComplete="family-name"
                    maxLength={150}
                    placeholder="Votre nom"
                    value={lastName}
                    onChange={(event) => setLastName(event.target.value)}
                  />
                </label>
              </div>
            )}

            <label className="login-field">
              <span>Numéro de téléphone</span>
              <div className="login-input-wrap">
                <span className="login-input-icon" aria-hidden="true">+223</span>
                <input
                  className="login-input-with-prefix"
                  autoComplete="tel"
                  inputMode="tel"
                  required
                  maxLength={16}
                  placeholder="+223 70 00 00 00"
                  value={phone}
                  onChange={(event) => setPhone(event.target.value)}
                />
              </div>
            </label>

            {mode === "register" && (
              <label className="login-field">
                <span>E-mail <small>(facultatif)</small></span>
                <input
                  autoComplete="email"
                  type="email"
                  placeholder="nom@exemple.com"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </label>
            )}

            <label className="login-field">
              <span>Mot de passe</span>
              <div className="login-input-wrap">
                <input
                  className="login-input-with-action"
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
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

            {mode === "register" && (
              <p className="login-hint">
                Minimum 8 caractères. Choisissez un mot de passe difficile à deviner.
              </p>
            )}

            {error && <p className="login-error" role="alert">{error}</p>}

            <button className="login-submit" disabled={busy} type="submit">
              {busy
                ? "Traitement…"
                : mode === "login"
                  ? "Se connecter"
                  : "Créer mon compte"}
            </button>
          </form>

          <p className="login-card-foot">
            Connexion protégée par BKO Services.
          </p>
        </div>
      </section>
    </main>
  );
}
