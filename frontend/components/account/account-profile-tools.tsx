"use client";

import { FormEvent, useMemo, useState } from "react";

import {
  apiFormMutation,
  apiMutation,
  type PublicUser,
} from "@/lib/client-api";

type Props = {
  user: PublicUser;
  refreshUser: () => Promise<void>;
  titlePrefix?: string;
};

function initials(user: PublicUser) {
  const source =
    [user.first_name, user.last_name].filter(Boolean).join(" ").trim() ||
    user.phone;
  return source
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join("");
}

export default function AccountProfileTools({
  user,
  refreshUser,
  titlePrefix = "Compte",
}: Props) {
  const [avatarBusy, setAvatarBusy] = useState(false);
  const [passwordBusy, setPasswordBusy] = useState(false);
  const [avatarMessage, setAvatarMessage] = useState("");
  const [avatarError, setAvatarError] = useState("");
  const [passwordMessage, setPasswordMessage] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPasswords, setShowPasswords] = useState(false);
  const avatarSrc = useMemo(
    () => (user.has_avatar && user.avatar_url ? `${user.avatar_url}?v=${user.id}` : ""),
    [user.avatar_url, user.has_avatar, user.id],
  );

  async function uploadAvatar(file: File | undefined) {
    if (!file) return;
    setAvatarError("");
    setAvatarMessage("");

    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setAvatarError("Formats autorisés : JPG, PNG ou WEBP.");
      return;
    }
    if (file.size > 3 * 1024 * 1024) {
      setAvatarError("La photo ne doit pas dépasser 3 Mo.");
      return;
    }

    setAvatarBusy(true);
    try {
      const formData = new FormData();
      formData.append("avatar", file);
      await apiFormMutation<PublicUser>("/api/v1/auth/avatar/", "PUT", formData);
      await refreshUser();
      setAvatarMessage("Photo de profil mise à jour.");
    } catch (caught) {
      setAvatarError(
        caught instanceof Error ? caught.message : "Impossible d’ajouter la photo.",
      );
    } finally {
      setAvatarBusy(false);
    }
  }

  async function removeAvatar() {
    setAvatarBusy(true);
    setAvatarError("");
    setAvatarMessage("");
    try {
      await apiMutation<PublicUser>("/api/v1/auth/avatar/", "DELETE");
      await refreshUser();
      setAvatarMessage("Photo supprimée.");
    } catch (caught) {
      setAvatarError(
        caught instanceof Error ? caught.message : "Impossible de supprimer la photo.",
      );
    } finally {
      setAvatarBusy(false);
    }
  }

  async function changePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPasswordError("");
    setPasswordMessage("");

    if (newPassword !== confirmPassword) {
      setPasswordError("Les deux nouveaux mots de passe ne correspondent pas.");
      return;
    }

    setPasswordBusy(true);
    try {
      await apiMutation<{ detail: string }>(
        "/api/v1/auth/change-password/",
        "POST",
        {
          current_password: currentPassword,
          new_password: newPassword,
          confirm_password: confirmPassword,
        },
      );
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setPasswordMessage("Mot de passe modifié avec succès.");
    } catch (caught) {
      setPasswordError(
        caught instanceof Error
          ? caught.message
          : "Impossible de modifier le mot de passe.",
      );
    } finally {
      setPasswordBusy(false);
    }
  }

  return (
    <div className="account-tools-grid">
      <section className="account-tool-card account-avatar-card">
        <div className="account-tool-heading">
          <span className="page-kicker">{titlePrefix}</span>
          <h2>Photo de profil</h2>
          <p>Ajoutez une photo claire pour personnaliser votre espace.</p>
        </div>

        <div className="account-avatar-editor">
          <div className="account-avatar-preview">
            {avatarSrc ? (
              <img src={avatarSrc} alt="Photo de profil" />
            ) : (
              <span>{initials(user)}</span>
            )}
          </div>

          <div className="account-avatar-actions">
            <label className="button-secondary account-upload-button">
              {avatarBusy ? "Mise à jour…" : "Choisir une photo"}
              <input
                accept="image/jpeg,image/png,image/webp"
                disabled={avatarBusy}
                type="file"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  void uploadAvatar(file);
                  event.currentTarget.value = "";
                }}
              />
            </label>

            {user.has_avatar && (
              <button
                className="button-danger-ghost"
                disabled={avatarBusy}
                type="button"
                onClick={removeAvatar}
              >
                Supprimer
              </button>
            )}
          </div>
        </div>

        <small className="account-tool-note">JPG, PNG ou WEBP · 3 Mo maximum.</small>
        {avatarMessage && <p className="form-success account-tool-feedback">{avatarMessage}</p>}
        {avatarError && <p className="inline-error account-tool-feedback">{avatarError}</p>}
      </section>

      <section className="account-tool-card">
        <div className="account-tool-heading">
          <span className="page-kicker">Sécurité</span>
          <h2>Changer le mot de passe</h2>
          <p>Votre mot de passe actuel est obligatoire avant toute modification.</p>
        </div>

        <form className="form-stack" onSubmit={changePassword}>
          <label className="field">
            <span>Mot de passe actuel</span>
            <input
              autoComplete="current-password"
              required
              type={showPasswords ? "text" : "password"}
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
            />
          </label>

          <label className="field">
            <span>Nouveau mot de passe</span>
            <input
              autoComplete="new-password"
              minLength={8}
              required
              type={showPasswords ? "text" : "password"}
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
            />
          </label>

          <label className="field">
            <span>Confirmer le nouveau mot de passe</span>
            <input
              autoComplete="new-password"
              minLength={8}
              required
              type={showPasswords ? "text" : "password"}
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
            />
          </label>

          <label className="account-show-password">
            <input
              checked={showPasswords}
              type="checkbox"
              onChange={(event) => setShowPasswords(event.target.checked)}
            />
            <span>Afficher les mots de passe</span>
          </label>

          {passwordMessage && (
            <p className="form-success account-tool-feedback">{passwordMessage}</p>
          )}
          {passwordError && (
            <p className="inline-error account-tool-feedback">{passwordError}</p>
          )}

          <button className="button-primary" disabled={passwordBusy} type="submit">
            {passwordBusy ? "Modification…" : "Modifier mon mot de passe"}
          </button>
        </form>
      </section>
    </div>
  );
}
