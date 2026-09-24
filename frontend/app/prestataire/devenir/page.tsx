"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  ApiReadError,
  apiGet,
  apiMutation,
  type ApiPage,
  type Category,
  type City,
  type Commune,
  type Neighborhood,
  type PublicUser,
  type Trade,
} from "@/lib/client-api";
import type { ProviderProfile } from "@/lib/provider-api";

type Stage = "loading" | "account" | "verify" | "application" | "status";
type AuthMode = "register" | "login";

function messageFromError(error: unknown) {
  return error instanceof Error
    ? error.message
    : "Une erreur inattendue est survenue.";
}

const STATUS_COPY: Record<
  ProviderProfile["status"],
  { label: string; title: string; description: string; tone: string }
> = {
  PENDING: {
    label: "En attente",
    title: "Votre dossier est en cours de vérification",
    description:
      "BKO Services doit vérifier votre dossier et votre identité avant d’activer l’espace prestataire.",
    tone: "pending",
  },
  VERIFIED: {
    label: "Approuvé",
    title: "Votre dossier est approuvé",
    description:
      "Votre compte prestataire est validé. Actualisez votre statut pour accéder à votre espace professionnel.",
    tone: "verified",
  },
  REJECTED: {
    label: "À corriger",
    title: "Votre dossier doit être corrigé",
    description:
      "Vous pouvez modifier les informations du dossier puis le renvoyer pour une nouvelle vérification.",
    tone: "rejected",
  },
  SUSPENDED: {
    label: "Suspendu",
    title: "Votre accès prestataire est suspendu",
    description:
      "Le dossier doit être rouvert par un administrateur habilité avant toute nouvelle modification.",
    tone: "suspended",
  },
};

export default function BecomeProviderPage() {
  const router = useRouter();
  const [stage, setStage] = useState<Stage>("loading");
  const [authMode, setAuthMode] = useState<AuthMode>("register");
  const [user, setUser] = useState<PublicUser | null>(null);
  const [application, setApplication] = useState<ProviderProfile | null>(null);
  const [editingApplication, setEditingApplication] = useState(false);

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [phone, setPhone] = useState("+223");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const [otpCode, setOtpCode] = useState("");
  const [otpRequested, setOtpRequested] = useState(false);

  const [legalName, setLegalName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [description, setDescription] = useState("");
  const [selectedTradeIds, setSelectedTradeIds] = useState<string[]>([]);
  const [selectedAreaIds, setSelectedAreaIds] = useState<string[]>([]);
  const [selectedTradeLabels, setSelectedTradeLabels] =
    useState<Record<string, string>>({});
  const [selectedAreaLabels, setSelectedAreaLabels] =
    useState<Record<string, string>>({});

  const [categories, setCategories] = useState<Category[]>([]);
  const [categoryId, setCategoryId] = useState("");
  const [trades, setTrades] = useState<Trade[]>([]);
  const [cities, setCities] = useState<City[]>([]);
  const [cityId, setCityId] = useState("");
  const [communes, setCommunes] = useState<Commune[]>([]);
  const [communeId, setCommuneId] = useState("");
  const [neighborhoods, setNeighborhoods] = useState<Neighborhood[]>([]);
  const [loadingOptions, setLoadingOptions] = useState(false);

  const [busy, setBusy] = useState(false);
  const [info, setInfo] = useState("");
  const [error, setError] = useState("");

  async function continueFlow(account: PublicUser) {
    setUser(account);

    if (account.role === "PROVIDER") {
      router.replace("/prestataire");
      router.refresh();
      return;
    }

    if (account.role !== "CLIENT") {
      setError("Ce compte ne peut pas déposer une candidature prestataire.");
      setStage("account");
      return;
    }

    if (!account.phone_verified_at) {
      setStage("verify");
      return;
    }

    try {
      const dossier = await apiGet<ProviderProfile>(
        "/api/v1/providers/application/",
      );
      setApplication(dossier);
      setStage("status");
    } catch (caught) {
      if (caught instanceof ApiReadError && caught.status === 404) {
        setApplication(null);
        setEditingApplication(false);
        setStage("application");
        return;
      }
      throw caught;
    }
  }

  useEffect(() => {
    let active = true;

    apiGet<PublicUser>("/api/v1/auth/me/")
      .then((account) => {
        if (!active) return;
        return continueFlow(account);
      })
      .catch((caught) => {
        if (!active) return;
        if (caught instanceof ApiReadError && caught.status === 401) {
          setStage("account");
          return;
        }
        setError(messageFromError(caught));
        setStage("account");
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (stage !== "application") return;

    let active = true;
    setLoadingOptions(true);

    Promise.all([
      apiGet<ApiPage<Category>>("/api/v1/catalog/categories/"),
      apiGet<ApiPage<City>>("/api/v1/locations/cities/"),
    ])
      .then(([categoryPage, cityPage]) => {
        if (!active) return;
        setCategories(categoryPage.results);
        setCities(cityPage.results);

        if (!cityId) {
          const bamako = cityPage.results.find(
            (city) => city.name.toLowerCase() === "bamako",
          );
          if (bamako) setCityId(bamako.id);
        }
      })
      .catch((caught) => {
        if (active) setError(messageFromError(caught));
      })
      .finally(() => {
        if (active) setLoadingOptions(false);
      });

    return () => {
      active = false;
    };
  }, [stage]);

  useEffect(() => {
    if (stage !== "application" || !categoryId) {
      setTrades([]);
      return;
    }

    let active = true;
    apiGet<ApiPage<Trade>>(
      "/api/v1/catalog/trades/?category=" + encodeURIComponent(categoryId),
    )
      .then((page) => {
        if (active) setTrades(page.results);
      })
      .catch((caught) => {
        if (active) setError(messageFromError(caught));
      });

    return () => {
      active = false;
    };
  }, [categoryId, stage]);

  useEffect(() => {
    if (stage !== "application" || !cityId) {
      setCommunes([]);
      return;
    }

    let active = true;
    apiGet<ApiPage<Commune>>(
      "/api/v1/locations/communes/?city=" + encodeURIComponent(cityId),
    )
      .then((page) => {
        if (active) setCommunes(page.results);
      })
      .catch((caught) => {
        if (active) setError(messageFromError(caught));
      });

    return () => {
      active = false;
    };
  }, [cityId, stage]);

  useEffect(() => {
    if (stage !== "application" || !communeId) {
      setNeighborhoods([]);
      return;
    }

    let active = true;
    apiGet<ApiPage<Neighborhood>>(
      "/api/v1/locations/neighborhoods/?commune=" +
        encodeURIComponent(communeId),
    )
      .then((page) => {
        if (active) setNeighborhoods(page.results);
      })
      .catch((caught) => {
        if (active) setError(messageFromError(caught));
      });

    return () => {
      active = false;
    };
  }, [communeId, stage]);

  const stepIndex = useMemo(() => {
    if (stage === "account") return 1;
    if (stage === "verify") return 2;
    if (stage === "application") return 3;
    if (stage === "status") return 4;
    return 1;
  }, [stage]);

  async function submitAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setInfo("");

    if (authMode === "register" && password !== confirmPassword) {
      setError("Les deux mots de passe ne correspondent pas.");
      return;
    }

    setBusy(true);
    try {
      if (authMode === "register") {
        await apiMutation<PublicUser>("/api/v1/auth/register/", "POST", {
          phone: phone.trim(),
          password,
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          email: email.trim(),
        });
      }

      const account = await apiMutation<PublicUser>(
        "/api/v1/auth/login/",
        "POST",
        {
          phone: phone.trim(),
          password,
        },
      );

      if (account.role === "PROVIDER") {
        router.replace("/prestataire");
        router.refresh();
        return;
      }

      if (account.role !== "CLIENT") {
        await apiMutation<void>("/api/v1/auth/logout/", "POST", {});
        throw new Error(
          "Ce compte ne peut pas déposer une candidature prestataire.",
        );
      }

      await continueFlow(account);
    } catch (caught) {
      setError(messageFromError(caught));
    } finally {
      setBusy(false);
    }
  }

  async function requestOtp() {
    setBusy(true);
    setError("");
    setInfo("");
    try {
      await apiMutation<{ detail: string }>(
        "/api/v1/auth/phone/request-code/",
        "POST",
        {},
      );
      setOtpRequested(true);
      setInfo(
        "Code envoyé. En développement local, le code apparaît dans le terminal Django.",
      );
    } catch (caught) {
      setError(messageFromError(caught));
    } finally {
      setBusy(false);
    }
  }

  async function verifyOtp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setInfo("");

    if (!/^\d{6}$/.test(otpCode)) {
      setError("Le code doit contenir exactement 6 chiffres.");
      return;
    }

    setBusy(true);
    try {
      await apiMutation("/api/v1/auth/phone/verify/", "POST", {
        code: otpCode,
      });
      const account = await apiGet<PublicUser>("/api/v1/auth/me/");
      await continueFlow(account);
    } catch (caught) {
      setError(messageFromError(caught));
    } finally {
      setBusy(false);
    }
  }

  function toggleTrade(trade: Trade) {
    setSelectedTradeIds((current) => {
      if (current.includes(trade.id)) {
        setSelectedTradeLabels((labels) => {
          const next = { ...labels };
          delete next[trade.id];
          return next;
        });
        return current.filter((id) => id !== trade.id);
      }

      if (current.length >= 10) {
        setError("Vous pouvez sélectionner au maximum 10 métiers.");
        return current;
      }

      setSelectedTradeLabels((labels) => ({
        ...labels,
        [trade.id]: trade.name,
      }));
      return [...current, trade.id];
    });
  }

  function toggleArea(area: Neighborhood) {
    const commune = communes.find((item) => item.id === area.commune);
    const label = commune ? area.name + " · " + commune.name : area.name;

    setSelectedAreaIds((current) => {
      if (current.includes(area.id)) {
        setSelectedAreaLabels((labels) => {
          const next = { ...labels };
          delete next[area.id];
          return next;
        });
        return current.filter((id) => id !== area.id);
      }

      if (current.length >= 30) {
        setError("Vous pouvez sélectionner au maximum 30 quartiers.");
        return current;
      }

      setSelectedAreaLabels((labels) => ({
        ...labels,
        [area.id]: label,
      }));
      return [...current, area.id];
    });
  }

  async function submitApplication(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setInfo("");

    if (!legalName.trim() || !displayName.trim()) {
      setError("Renseignez votre nom légal et votre nom public.");
      return;
    }
    if (selectedTradeIds.length === 0) {
      setError("Choisissez au moins un métier.");
      return;
    }
    if (selectedAreaIds.length === 0) {
      setError("Choisissez au moins un quartier d’intervention.");
      return;
    }

    setBusy(true);
    try {
      const dossier = await apiMutation<ProviderProfile>(
        "/api/v1/providers/application/",
        editingApplication ? "PATCH" : "POST",
        {
          legal_name: legalName.trim(),
          display_name: displayName.trim(),
          description: description.trim(),
          trade_ids: selectedTradeIds,
          area_ids: selectedAreaIds,
        },
      );

      setApplication(dossier);
      setEditingApplication(false);
      setStage("status");
      setInfo(
        "Votre dossier a été enregistré et transmis à BKO Services pour vérification.",
      );
    } catch (caught) {
      setError(messageFromError(caught));
    } finally {
      setBusy(false);
    }
  }

  function editApplication() {
    if (!application) return;

    setLegalName(application.legal_name);
    setDisplayName(application.display_name);
    setDescription(application.description);
    setSelectedTradeIds(application.trades);
    setSelectedAreaIds(application.service_areas);
    setSelectedTradeLabels(
      Object.fromEntries(
        application.trade_details.map((trade) => [trade.id, trade.name]),
      ),
    );
    setSelectedAreaLabels(
      Object.fromEntries(
        application.service_area_details.map((area) => [
          area.id,
          area.name + " · " + area.commune_name,
        ]),
      ),
    );
    setEditingApplication(true);
    setError("");
    setInfo("");
    setStage("application");
  }

  async function refreshStatus() {
    setBusy(true);
    setError("");
    setInfo("");
    try {
      const account = await apiGet<PublicUser>("/api/v1/auth/me/");
      await continueFlow(account);
      if (account.role === "CLIENT") {
        setInfo("Statut actualisé.");
      }
    } catch (caught) {
      setError(messageFromError(caught));
    } finally {
      setBusy(false);
    }
  }

  async function logoutCandidate() {
    try {
      await apiMutation<void>("/api/v1/auth/logout/", "POST", {});
    } finally {
      setUser(null);
      setApplication(null);
      setOtpCode("");
      setOtpRequested(false);
      setPassword("");
      setConfirmPassword("");
      setStage("account");
    }
  }

  const statusCopy = application ? STATUS_COPY[application.status] : null;

  return (
    <main className="provider-onboarding">
      <section className="provider-onboarding-side">
        <Link className="provider-onboarding-brand" href="/">
          <span className="login-brand-mark" aria-hidden="true">B</span>
          <span>
            <strong>BKO Services</strong>
            <small>Réseau prestataires</small>
          </span>
        </Link>

        <div className="provider-onboarding-side-copy">
          <span className="login-badge">Devenir prestataire</span>
          <h1>Votre savoir-faire mérite plus d’opportunités.</h1>
          <p>
            Créez votre dossier professionnel, choisissez vos métiers et vos
            zones d’intervention, puis faites valider votre profil par BKO Services.
          </p>

          <div className="provider-onboarding-benefits">
            <span><b>✓</b> Offres adaptées à vos métiers</span>
            <span><b>✓</b> Zones d’intervention choisies</span>
            <span><b>✓</b> Profil vérifié avant activation</span>
          </div>
        </div>

        <Link className="provider-existing-login" href="/prestataire/connexion">
          Déjà prestataire validé ? Se connecter
        </Link>
      </section>

      <section className="provider-onboarding-main">
        <div className="provider-onboarding-card">
          <div className="provider-stepper" aria-label="Étapes de candidature">
            {[
              ["1", "Compte"],
              ["2", "Téléphone"],
              ["3", "Dossier"],
              ["4", "Validation"],
            ].map(([number, label], index) => {
              const numberValue = index + 1;
              const active = numberValue === stepIndex;
              const done = numberValue < stepIndex;
              return (
                <div
                  className={
                    done
                      ? "provider-step done"
                      : active
                        ? "provider-step active"
                        : "provider-step"
                  }
                  key={number}
                >
                  <span>{done ? "✓" : number}</span>
                  <small>{label}</small>
                </div>
              );
            })}
          </div>

          {stage === "loading" && (
            <div className="provider-onboarding-loading">
              <div className="loading-spinner" aria-hidden="true" />
              <p>Vérification de votre parcours…</p>
            </div>
          )}

          {stage === "account" && (
            <>
              <div className="provider-onboarding-heading">
                <span className="page-kicker">Étape 1</span>
                <h2>
                  {authMode === "register"
                    ? "Créer mon compte"
                    : "Utiliser mon compte existant"}
                </h2>
                <p>
                  Votre compte reste Client pendant l’étude du dossier. Il devient
                  Prestataire uniquement après approbation par BKO Services.
                </p>
              </div>

              <div className="login-tabs provider-onboarding-tabs">
                <button
                  className={authMode === "register" ? "active" : ""}
                  type="button"
                  onClick={() => {
                    setAuthMode("register");
                    setError("");
                  }}
                >
                  Nouveau compte
                </button>
                <button
                  className={authMode === "login" ? "active" : ""}
                  type="button"
                  onClick={() => {
                    setAuthMode("login");
                    setError("");
                  }}
                >
                  J’ai déjà un compte
                </button>
              </div>

              <form className="login-form" onSubmit={submitAccount}>
                {authMode === "register" && (
                  <div className="login-grid-two">
                    <label className="login-field">
                      <span>Prénom</span>
                      <input
                        autoComplete="given-name"
                        maxLength={150}
                        required
                        value={firstName}
                        onChange={(event) => setFirstName(event.target.value)}
                      />
                    </label>
                    <label className="login-field">
                      <span>Nom</span>
                      <input
                        autoComplete="family-name"
                        maxLength={150}
                        required
                        value={lastName}
                        onChange={(event) => setLastName(event.target.value)}
                      />
                    </label>
                  </div>
                )}

                <label className="login-field">
                  <span>Numéro de téléphone</span>
                  <input
                    autoComplete="tel"
                    inputMode="tel"
                    maxLength={16}
                    placeholder="+223 70 00 00 00"
                    required
                    value={phone}
                    onChange={(event) => setPhone(event.target.value)}
                  />
                </label>

                {authMode === "register" && (
                  <label className="login-field">
                    <span>E-mail <small>(facultatif)</small></span>
                    <input
                      autoComplete="email"
                      type="email"
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
                      autoComplete={
                        authMode === "register"
                          ? "new-password"
                          : "current-password"
                      }
                      minLength={8}
                      required
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                    />
                    <button
                      className="login-input-action"
                      type="button"
                      onClick={() => setShowPassword((current) => !current)}
                    >
                      {showPassword ? "Masquer" : "Afficher"}
                    </button>
                  </div>
                </label>

                {authMode === "register" && (
                  <label className="login-field">
                    <span>Confirmer le mot de passe</span>
                    <input
                      autoComplete="new-password"
                      minLength={8}
                      required
                      type={showPassword ? "text" : "password"}
                      value={confirmPassword}
                      onChange={(event) => setConfirmPassword(event.target.value)}
                    />
                  </label>
                )}

                {error && <p className="login-error" role="alert">{error}</p>}

                <button className="login-submit" disabled={busy} type="submit">
                  {busy
                    ? "Traitement…"
                    : authMode === "register"
                      ? "Créer et continuer"
                      : "Se connecter et continuer"}
                </button>
              </form>
            </>
          )}

          {stage === "verify" && user && (
            <>
              <div className="provider-onboarding-heading">
                <span className="page-kicker">Étape 2</span>
                <h2>Vérifier votre téléphone</h2>
                <p>
                  Nous vérifions que le numéro <strong>{user.phone}</strong> vous
                  appartient avant d’accepter un dossier professionnel.
                </p>
              </div>

              <div className="provider-otp-box">
                <span className="provider-otp-icon" aria-hidden="true">SMS</span>
                <div>
                  <strong>Code de sécurité à 6 chiffres</strong>
                  <p>Le code expire rapidement et ne peut être utilisé qu’une fois.</p>
                </div>
              </div>

              <form className="login-form" onSubmit={verifyOtp}>
                <button
                  className="button-secondary provider-full-button"
                  disabled={busy}
                  type="button"
                  onClick={requestOtp}
                >
                  {otpRequested ? "Renvoyer un code" : "Recevoir mon code"}
                </button>

                <label className="login-field provider-otp-input">
                  <span>Code reçu</span>
                  <input
                    autoComplete="one-time-code"
                    inputMode="numeric"
                    maxLength={6}
                    pattern="\d{6}"
                    placeholder="000000"
                    required
                    value={otpCode}
                    onChange={(event) =>
                      setOtpCode(
                        event.target.value.replace(/\D/g, "").slice(0, 6),
                      )
                    }
                  />
                </label>

                {info && <p className="password-reset-info">{info}</p>}
                {error && <p className="login-error" role="alert">{error}</p>}

                <button
                  className="login-submit"
                  disabled={busy || otpCode.length !== 6}
                  type="submit"
                >
                  {busy ? "Vérification…" : "Vérifier et continuer"}
                </button>
              </form>

              <button
                className="password-reset-back"
                type="button"
                onClick={logoutCandidate}
              >
                Utiliser un autre compte
              </button>
            </>
          )}

          {stage === "application" && user && (
            <>
              <div className="provider-onboarding-heading">
                <span className="page-kicker">Étape 3</span>
                <h2>
                  {editingApplication
                    ? "Modifier mon dossier"
                    : "Mon dossier professionnel"}
                </h2>
                <p>
                  Choisissez uniquement les métiers que vous exercez réellement
                  et les quartiers où vous pouvez intervenir.
                </p>
              </div>

              {editingApplication && (
                <div className="provider-edit-warning">
                  <strong>Nouvelle vérification nécessaire</strong>
                  <p>
                    Toute modification d’un dossier déjà contrôlé peut nécessiter
                    une nouvelle validation par BKO Services.
                  </p>
                </div>
              )}

              <form
                className="provider-application-form"
                onSubmit={submitApplication}
              >
                <section className="provider-form-section">
                  <div className="provider-form-section-head">
                    <span>01</span>
                    <div>
                      <h3>Votre activité</h3>
                      <p>Nom légal, nom affiché aux clients et présentation.</p>
                    </div>
                  </div>

                  <div className="form-stack">
                    <div className="form-grid two">
                      <label className="field">
                        <span>Nom légal *</span>
                        <input
                          maxLength={150}
                          placeholder="Nom complet / raison sociale"
                          required
                          value={legalName}
                          onChange={(event) => setLegalName(event.target.value)}
                        />
                      </label>
                      <label className="field">
                        <span>Nom public *</span>
                        <input
                          maxLength={120}
                          placeholder="Ex. Atelier Traoré"
                          required
                          value={displayName}
                          onChange={(event) => setDisplayName(event.target.value)}
                        />
                      </label>
                    </div>

                    <label className="field">
                      <span>Présentation</span>
                      <textarea
                        maxLength={1000}
                        placeholder="Présentez brièvement votre expérience et vos services."
                        rows={4}
                        value={description}
                        onChange={(event) => setDescription(event.target.value)}
                      />
                    </label>
                  </div>
                </section>

                <section className="provider-form-section">
                  <div className="provider-form-section-head">
                    <span>02</span>
                    <div>
                      <h3>Métiers</h3>
                      <p>
                        Maximum 10 métiers. Vous pouvez changer de catégorie sans
                        perdre vos choix.
                      </p>
                    </div>
                  </div>

                  <label className="field">
                    <span>Catégorie</span>
                    <select
                      disabled={loadingOptions}
                      value={categoryId}
                      onChange={(event) => setCategoryId(event.target.value)}
                    >
                      <option value="">Choisir une catégorie</option>
                      {categories.map((category) => (
                        <option key={category.id} value={category.id}>
                          {category.name}
                        </option>
                      ))}
                    </select>
                  </label>

                  {categoryId && (
                    <div className="provider-choice-grid">
                      {trades.map((trade) => (
                        <label
                          className={
                            selectedTradeIds.includes(trade.id)
                              ? "provider-choice active"
                              : "provider-choice"
                          }
                          key={trade.id}
                        >
                          <input
                            checked={selectedTradeIds.includes(trade.id)}
                            type="checkbox"
                            onChange={() => toggleTrade(trade)}
                          />
                          <span>
                            <strong>{trade.name}</strong>
                            {trade.description && (
                              <small>{trade.description}</small>
                            )}
                          </span>
                        </label>
                      ))}
                    </div>
                  )}

                  {selectedTradeIds.length > 0 && (
                    <div className="provider-selected-summary">
                      <strong>
                        {selectedTradeIds.length} métier(s) sélectionné(s)
                      </strong>
                      <div>
                        {selectedTradeIds.map((id) => (
                          <span key={id}>
                            {selectedTradeLabels[id] || "Métier sélectionné"}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </section>

                <section className="provider-form-section">
                  <div className="provider-form-section-head">
                    <span>03</span>
                    <div>
                      <h3>Zones d’intervention</h3>
                      <p>
                        Sélectionnez les quartiers où vous pouvez réellement vous
                        déplacer.
                      </p>
                    </div>
                  </div>

                  <div className="form-grid two">
                    <label className="field">
                      <span>Ville</span>
                      <select
                        value={cityId}
                        onChange={(event) => {
                          setCityId(event.target.value);
                          setCommuneId("");
                        }}
                      >
                        <option value="">Choisir une ville</option>
                        {cities.map((city) => (
                          <option key={city.id} value={city.id}>
                            {city.name}
                          </option>
                        ))}
                      </select>
                    </label>

                    <label className="field">
                      <span>Commune</span>
                      <select
                        disabled={!cityId}
                        value={communeId}
                        onChange={(event) => setCommuneId(event.target.value)}
                      >
                        <option value="">Choisir une commune</option>
                        {communes.map((commune) => (
                          <option key={commune.id} value={commune.id}>
                            {commune.name}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>

                  {communeId && (
                    <div className="provider-choice-grid">
                      {neighborhoods.map((area) => (
                        <label
                          className={
                            selectedAreaIds.includes(area.id)
                              ? "provider-choice active"
                              : "provider-choice"
                          }
                          key={area.id}
                        >
                          <input
                            checked={selectedAreaIds.includes(area.id)}
                            type="checkbox"
                            onChange={() => toggleArea(area)}
                          />
                          <span>
                            <strong>{area.name}</strong>
                          </span>
                        </label>
                      ))}
                    </div>
                  )}

                  {selectedAreaIds.length > 0 && (
                    <div className="provider-selected-summary">
                      <strong>
                        {selectedAreaIds.length} quartier(s) sélectionné(s)
                      </strong>
                      <div>
                        {selectedAreaIds.map((id) => (
                          <span key={id}>
                            {selectedAreaLabels[id] || "Quartier sélectionné"}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </section>

                {info && <p className="form-success">{info}</p>}
                {error && <p className="form-error" role="alert">{error}</p>}

                <div className="provider-application-actions">
                  {editingApplication && (
                    <button
                      className="button-secondary"
                      type="button"
                      onClick={() => setStage("status")}
                    >
                      Annuler
                    </button>
                  )}
                  <button
                    className="login-submit"
                    disabled={busy}
                    type="submit"
                  >
                    {busy
                      ? "Enregistrement…"
                      : editingApplication
                        ? "Enregistrer et renvoyer"
                        : "Envoyer mon dossier"}
                  </button>
                </div>
              </form>
            </>
          )}

          {stage === "status" && application && statusCopy && (
            <>
              <div className="provider-status-view">
                <span
                  className={"provider-status-symbol " + statusCopy.tone}
                  aria-hidden="true"
                >
                  {application.status === "VERIFIED"
                    ? "✓"
                    : application.status === "REJECTED"
                      ? "!"
                      : application.status === "SUSPENDED"
                        ? "×"
                        : "…"}
                </span>

                <span
                  className={"provider-status-pill " + statusCopy.tone}
                >
                  {statusCopy.label}
                </span>
                <h2>{statusCopy.title}</h2>
                <p>{statusCopy.description}</p>
              </div>

              <div className="provider-status-details">
                <div>
                  <small>Nom public</small>
                  <strong>{application.display_name}</strong>
                </div>
                <div>
                  <small>Métiers</small>
                  <strong>{application.trade_details.length}</strong>
                </div>
                <div>
                  <small>Zones</small>
                  <strong>{application.service_area_details.length}</strong>
                </div>
              </div>

              <div className="provider-status-tags">
                {application.trade_details.map((trade) => (
                  <span key={trade.id}>{trade.name}</span>
                ))}
                {application.service_area_details.slice(0, 6).map((area) => (
                  <span key={area.id}>
                    {area.name} · {area.commune_name}
                  </span>
                ))}
              </div>

              {info && <p className="form-success">{info}</p>}
              {error && <p className="login-error" role="alert">{error}</p>}

              <div className="provider-status-actions">
                <button
                  className="button-primary"
                  disabled={busy}
                  type="button"
                  onClick={refreshStatus}
                >
                  {busy ? "Actualisation…" : "Actualiser mon statut"}
                </button>

                {(application.status === "PENDING" ||
                  application.status === "REJECTED") && (
                  <button
                    className="button-secondary"
                    type="button"
                    onClick={editApplication}
                  >
                    Modifier mon dossier
                  </button>
                )}

                {user?.role === "CLIENT" && (
                  <Link className="button-secondary" href="/client">
                    Retour à mon espace client
                  </Link>
                )}
              </div>

              <button
                className="password-reset-back"
                type="button"
                onClick={logoutCandidate}
              >
                Se déconnecter
              </button>
            </>
          )}
        </div>
      </section>
    </main>
  );
}
