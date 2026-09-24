"use client";
/* eslint-disable @next/next/no-img-element -- private authenticated avatar URLs intentionally bypass image optimization. */

import { FormEvent, useState } from "react";

import AccountProfileTools from "@/components/account/account-profile-tools";
import { useAdminSession } from "@/components/admin/admin-shell";
import { apiMutation } from "@/lib/client-api";

function initials(firstName: string, lastName: string, phone: string) {
  const source = [firstName, lastName].filter(Boolean).join(" ").trim() || phone;
  return source
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join("");
}

export default function AdminProfilePage() {
  const { user, refreshUser } = useAdminSession();
  const [firstName, setFirstName] = useState(user.first_name);
  const [lastName, setLastName] = useState(user.last_name);
  const [email, setEmail] = useState(user.email);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    setError("");
    try {
      await apiMutation("/api/v1/auth/me/", "PATCH", {
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        email: email.trim(),
      });
      await refreshUser();
      setMessage("Profil administrateur mis à jour.");
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Mise à jour impossible.",
      );
    } finally {
      setBusy(false);
    }
  }

  const fullName =
    [user.first_name, user.last_name].filter(Boolean).join(" ") || user.role;

  return (
    <main className="premium-profile-page">
      <section className="premium-profile-hero admin-profile-hero">
        <div className="premium-profile-avatar">
          {user.has_avatar && user.avatar_url ? (
            <img src={user.avatar_url} alt={fullName} />
          ) : (
            <span>{initials(user.first_name, user.last_name, user.phone)}</span>
          )}
        </div>
        <div className="premium-profile-identity">
          <span className="premium-profile-role">Administration BKO Services</span>
          <h1>{fullName}</h1>
          <p>Compte sécurisé pour la supervision de la plateforme.</p>
          <div className="premium-profile-badges">
            <span>{user.phone}</span>
            <span className="verified">{user.role}</span>
          </div>
        </div>
      </section>

      {message && <div className="form-success premium-profile-message">{message}</div>}
      {error && <div className="inline-error premium-profile-message">{error}</div>}

      <section className="account-tool-card premium-personal-card premium-admin-personal">
        <div className="account-tool-heading">
          <span className="page-kicker">Mon compte</span>
          <h2>Informations administrateur</h2>
          <p>
            Ces informations concernent votre propre compte et ne modifient pas
            vos permissions d’administration.
          </p>
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
          </label>

          <button className="button-primary" disabled={busy} type="submit">
            {busy ? "Enregistrement…" : "Enregistrer mes informations"}
          </button>
        </form>
      </section>

      <AccountProfileTools
        user={user}
        refreshUser={refreshUser}
        titlePrefix="Identité administrateur"
      />
    </main>
  );
}
