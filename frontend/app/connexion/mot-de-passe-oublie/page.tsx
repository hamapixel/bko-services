"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { getCsrfToken } from "@/lib/client-api";
import { sendJsonMutation } from "@/lib/safe-api";

type Step = "phone" | "code" | "done";

function messageFromError(error: unknown) {
  return error instanceof Error
    ? error.message
    : "Une erreur inattendue est survenue.";
}

export default function ForgotPasswordPage() {
  const [step, setStep] = useState<Step>("phone");
  const [phone, setPhone] = useState("+223");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  async function requestCode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setInfo("");

    try {
      const csrfToken = await getCsrfToken();
      const response = await sendJsonMutation<{ detail: string }>(
        "/api/v1/auth/password-reset/request/",
        "POST",
        {
          csrfToken,
          body: { phone: phone.trim() },
        },
      );
      setInfo(response.detail);
      setStep("code");
    } catch (caught) {
      setError(messageFromError(caught));
    } finally {
      setBusy(false);
    }
  }

  async function resetPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setInfo("");

    if (!/^\d{6}$/.test(code)) {
      setError("Le code doit contenir exactement 6 chiffres.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Les deux mots de passe ne correspondent pas.");
      return;
    }

    setBusy(true);
    try {
      const csrfToken = await getCsrfToken();
      await sendJsonMutation<{ detail: string }>(
        "/api/v1/auth/password-reset/confirm/",
        "POST",
        {
          csrfToken,
          body: {
            phone: phone.trim(),
            code,
            new_password: password,
            confirm_password: confirmPassword,
          },
        },
      );
      setStep("done");
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
          <span className="login-badge">Compte client</span>
          <h1>Retrouvez l’accès à votre compte.</h1>
          <p>
            Un code temporaire protège la réinitialisation de votre mot de passe.
          </p>
          <div className="login-points" aria-label="Sécurité">
            <span>Code à 6 chiffres</span>
            <span>Expiration rapide</span>
            <span>Usage unique</span>
          </div>
        </div>

        <p className="login-visual-foot">BKO Services · Assistance compte client</p>
      </section>

      <section className="login-card-zone">
        <div className="login-card">
          {step === "done" ? (
            <div className="password-reset-success">
              <span className="password-reset-success-icon" aria-hidden="true">✓</span>
              <span className="login-kicker">Terminé</span>
              <h2>Mot de passe modifié</h2>
              <p>
                Vous pouvez maintenant vous connecter avec votre nouveau mot de passe.
              </p>
              <Link className="login-submit password-reset-link-button" href="/connexion">
                Retour à la connexion
              </Link>
            </div>
          ) : (
            <>
              <div className="login-card-head">
                <span className="login-kicker">Mot de passe oublié</span>
                <h2>{step === "phone" ? "Réinitialiser" : "Vérifier le code"}</h2>
                <p>
                  {step === "phone"
                    ? "Saisissez le numéro associé à votre compte client."
                    : "Entrez le code reçu puis choisissez un nouveau mot de passe."}
                </p>
              </div>

              {step === "phone" ? (
                <form className="login-form" onSubmit={requestCode}>
                  <label className="login-field">
                    <span>Numéro de téléphone</span>
                    <div className="login-input-wrap">
                      <span className="login-input-icon" aria-hidden="true">Tél.</span>
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

                  {error && <p className="login-error" role="alert">{error}</p>}

                  <button className="login-submit" disabled={busy} type="submit">
                    {busy ? "Envoi…" : "Recevoir le code"}
                  </button>
                </form>
              ) : (
                <form className="login-form" onSubmit={resetPassword}>
                  {info && <p className="password-reset-info">{info}</p>}

                  <label className="login-field">
                    <span>Code à 6 chiffres</span>
                    <input
                      autoComplete="one-time-code"
                      inputMode="numeric"
                      maxLength={6}
                      pattern="\d{6}"
                      placeholder="000000"
                      required
                      value={code}
                      onChange={(event) =>
                        setCode(event.target.value.replace(/\D/g, "").slice(0, 6))
                      }
                    />
                  </label>

                  <label className="login-field">
                    <span>Nouveau mot de passe</span>
                    <div className="login-input-wrap">
                      <input
                        className="login-input-with-action"
                        autoComplete="new-password"
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

                  <label className="login-field">
                    <span>Confirmer le mot de passe</span>
                    <input
                      autoComplete="new-password"
                      minLength={8}
                      required
                      type={showPassword ? "text" : "password"}
                      placeholder="••••••••"
                      value={confirmPassword}
                      onChange={(event) => setConfirmPassword(event.target.value)}
                    />
                  </label>

                  {error && <p className="login-error" role="alert">{error}</p>}

                  <button className="login-submit" disabled={busy} type="submit">
                    {busy ? "Vérification…" : "Changer le mot de passe"}
                  </button>

                  <button
                    className="password-reset-back"
                    type="button"
                    onClick={() => {
                      setStep("phone");
                      setCode("");
                      setPassword("");
                      setConfirmPassword("");
                      setError("");
                      setInfo("");
                    }}
                  >
                    Modifier le numéro
                  </button>
                </form>
              )}

              <div className="login-links">
                <Link href="/connexion">← Retour à la connexion</Link>
              </div>
            </>
          )}
        </div>
      </section>
    </main>
  );
}
