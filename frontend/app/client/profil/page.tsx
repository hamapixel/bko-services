"use client";

import { FormEvent, useState } from "react";

import AccountProfileTools from "@/components/account/account-profile-tools";
import { useClientSession } from "@/components/client/client-shell";
import { apiMutation } from "@/lib/client-api";

function initials(firstName: string, lastName: string, phone: string) {
  const source = [firstName, lastName].filter(Boolean).join(" ").trim() || phone;
  return source
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join("");
}

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

  const fullName =
    [user.first_name, user.last_name].filter(Boolean).join(" ") || "Client BKO";

  return (
    <main className="premium-profile-page">
      <section className="premium-profile-hero client-profile-hero">
        <div className="premium-profile-avatar">
          {user.has_avatar && user.avatar_url ? (
            <img src={user.avatar_url} alt={fullName} />
          ) : (
            <span>{initials(user.first_name, user.last_name, user.phone)}</span>
          )}
        </div>

        <div className="premium-profile-identity">
          <span className="premium-profile-role">Compte client</span>
          <h1>{fullName}</h1>
          <p>{user.email || "Ajoutez votre adresse e-mail à votre profil."}</p>
          <div className="premium-profile-badges">
            <span>{user.phone}</span>
            <span className={user.phone_verified_at ? "verified" : "pending"}>
              {user.phone_verified_at ? "✓ Téléphone vérifié" : "Téléphone à vérifier"}
            </span>
          </div>
        </div>
      </section>

      {message && <div className="form-success premium-profile-message">{message}</div>}
      {error && <div className="inline-error premium-profile-message">{error}</div>}

      <div className="premium-profile-main-grid">
        <section className="account-tool-card premium-personal-card">
          <div className="account-tool-heading">
            <span className="page-kicker">Informations</span>
            <h2>Informations personnelles</h2>
            <p>Gardez vos coordonnées à jour pour faciliter vos interventions.</p>
          </div>

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
              <small>Le numéro utilisé pour la connexion ne se modifie pas ici.</small>
            </label>

            <button className="button-primary" disabled={busy} type="submit">
              {busy ? "Enregistrement…" : "Enregistrer mes informations"}
            </button>
          </form>
        </section>

        <section className="account-tool-card premium-verification-card">
          <div className="account-tool-heading">
            <span className="page-kicker">Sécurité du compte</span>
            <h2>Vérification du téléphone</h2>
            <p>
              Le numéro vérifié protège votre compte et permet au prestataire
              attribué de vous contacter.
            </p>
          </div>

          {user.phone_verified_at ? (
            <div className="premium-verified-panel">
              <span className="premium-verified-icon">✓</span>
              <div>
                <strong>Numéro vérifié</strong>
                <p>Votre compte peut envoyer des demandes de service.</p>
              </div>
            </div>
          ) : (
            <div className="form-stack">
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

      <AccountProfileTools
        user={user}
        refreshUser={refreshUser}
        titlePrefix="Personnalisation"
      />
    </main>
  );
}
