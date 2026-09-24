"use client";

import { FormEvent, useState } from "react";

import { useClientSession } from "@/components/client/client-shell";
import { apiMutation } from "@/lib/client-api";

export default function ClientProfilePage() {
  const { user, refreshUser } = useClientSession();
  const [firstName, setFirstName] = useState(user.first_name);
  const [lastName, setLastName] = useState(user.last_name);
  const [email, setEmail] = useState(user.email);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    setError("");
    try {
      await apiMutation(
        "/api/v1/auth/me/",
        "PATCH",
        {
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          email: email.trim(),
        },
      );
      await refreshUser();
      setMessage("Profil mis à jour.");
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Mise à jour impossible.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function requestCode() {
    setBusy(true);
    setMessage("");
    setError("");
    try {
      await apiMutation<{ detail: string }>(
        "/api/v1/auth/phone/request-code/",
        "POST",
        {},
      );
      setMessage(
        "Code demandé. En développement, consultez le terminal Django si le transport SMS console est utilisé.",
      );
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Envoi du code impossible.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function verifyCode() {
    if (!/^\d{6}$/.test(code)) {
      setError("Le code doit contenir exactement 6 chiffres.");
      return;
    }

    setBusy(true);
    setMessage("");
    setError("");
    try {
      await apiMutation(
        "/api/v1/auth/phone/verify/",
        "POST",
        { code },
      );
      await refreshUser();
      setCode("");
      setMessage("Numéro de téléphone vérifié.");
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Vérification du code impossible.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <section className="client-page-head">
        <div>
          <p className="page-kicker">Mon compte</p>
          <h1>Profil client</h1>
          <p>Vos informations de contact et la sécurité du compte.</p>
        </div>
      </section>

      {message && <div className="form-success">{message}</div>}
      {error && <div className="inline-error">{error}</div>}

      <div className="profile-grid">
        <section className="detail-card">
          <h2>Informations personnelles</h2>
          <form className="form-stack" onSubmit={saveProfile}>
            <div className="form-grid two">
              <label className="field">
                <span>Prénom</span>
                <input
                  maxLength={150}
                  value={firstName}
                  onChange={(event) => setFirstName(event.target.value)}
                />
              </label>
              <label className="field">
                <span>Nom</span>
                <input
                  maxLength={150}
                  value={lastName}
                  onChange={(event) => setLastName(event.target.value)}
                />
              </label>
            </div>
            <label className="field">
              <span>E-mail</span>
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </label>
            <label className="field">
              <span>Téléphone</span>
              <input disabled value={user.phone} />
              <small>Le numéro de connexion ne se modifie pas ici.</small>
            </label>
            <button className="button-primary" disabled={busy} type="submit">
              Enregistrer
            </button>
          </form>
        </section>

        <section className="detail-card">
          <p className="page-kicker">Sécurité</p>
          <h2>Vérification du téléphone</h2>

          {user.phone_verified_at ? (
            <div className="verified-box">
              <strong>✓ Numéro vérifié</strong>
              <p>
                Votre compte peut créer des demandes de service.
              </p>
            </div>
          ) : (
            <div className="form-stack">
              <p>
                Un code à 6 chiffres est nécessaire avant l’envoi de votre
                première demande.
              </p>
              <button
                className="button-secondary"
                disabled={busy}
                type="button"
                onClick={requestCode}
              >
                Recevoir un code
              </button>
              <label className="field">
                <span>Code reçu</span>
                <input
                  inputMode="numeric"
                  maxLength={6}
                  pattern="\d{6}"
                  placeholder="000000"
                  value={code}
                  onChange={(event) =>
                    setCode(event.target.value.replace(/\D/g, "").slice(0, 6))
                  }
                />
              </label>
              <button
                className="button-primary"
                disabled={busy || code.length !== 6}
                type="button"
                onClick={verifyCode}
              >
                Vérifier mon numéro
              </button>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
