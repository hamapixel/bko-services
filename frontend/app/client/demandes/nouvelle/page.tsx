"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { useClientSession } from "@/components/client/client-shell";
import {
  apiGetAll,
  apiMutation,
  type Category,
  type City,
  type Commune,
  type Neighborhood,
  type Region,
  type ServiceRequest,
  type Trade,
} from "@/lib/client-api";
import {
  createRequestDraft,
  deleteRequestDraft,
  getRequestDraft,
  saveRequestDraft,
  type RequestDraft,
  type RequestDraftPayload,
} from "@/lib/offline-drafts";
import { OfflineActionError } from "@/lib/safe-api";

type FormState = RequestDraftPayload & {
  category: string;
  region: string;
  city: string;
  commune: string;
};

const EMPTY_FORM: FormState = {
  category: "",
  region: "",
  trade: "",
  city: "",
  commune: "",
  neighborhood: "",
  title: "",
  description: "",
  address_detail: "",
  priority: "NORMAL",
};

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Une erreur est survenue.";
}

export default function NewClientRequestPage() {
  const router = useRouter();
  const { user } = useClientSession();
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [categories, setCategories] = useState<Category[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [cities, setCities] = useState<City[]>([]);
  const [regions, setRegions] = useState<Region[]>([]);
  const [communes, setCommunes] = useState<Commune[]>([]);
  const [neighborhoods, setNeighborhoods] = useState<Neighborhood[]>([]);
  const [draft, setDraft] = useState<RequestDraft | null>(null);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const sending = useRef(false);

  useEffect(() => {
    let active = true;
    const draftId =
      typeof window !== "undefined"
        ? new URLSearchParams(window.location.search).get("draft")
        : null;

    Promise.all([
      apiGetAll<Category>("/api/v1/catalog/categories/"),
      apiGetAll<Region>("/api/v1/locations/regions/"),
      draftId ? getRequestDraft(draftId, user.id) : Promise.resolve(null),
    ])
      .then(([categoryItems, regionItems, localDraft]) => {
        if (!active) return;
        setCategories(categoryItems);
        setRegions(regionItems);
        setDraft(localDraft);

        if (draftId && !localDraft) {
          setError("Ce brouillon n’est pas disponible pour votre compte sur cet appareil.");
        }

        if (localDraft) {
          setForm({
            category: localDraft.context?.category ?? "",
            region: localDraft.context?.region ?? regionItems.find(
              (region) => region.name.toLowerCase() === "district de bamako",
            )?.id ?? "",
            trade: localDraft.payload.trade,
            city: localDraft.context?.city ?? "",
            commune: localDraft.context?.commune ?? "",
            neighborhood: localDraft.payload.neighborhood,
            title: localDraft.payload.title,
            description: localDraft.payload.description,
            address_detail: localDraft.payload.address_detail,
            priority: localDraft.payload.priority,
          });
        } else {
          const bamakoDistrict = regionItems.find(
            (region) => region.name.toLowerCase() === "district de bamako",
          );
          if (bamakoDistrict) {
            setForm((current) => ({ ...current, region: bamakoDistrict.id }));
          }
        }
      })
      .catch((caught) => {
        if (active) setError(errorMessage(caught));
      })
      .finally(() => {
        if (active) setLoadingOptions(false);
      });

    return () => {
      active = false;
    };
  }, [user.id]);

  useEffect(() => {
    if (!form.region) return;
    let active = true;
    apiGetAll<City>(`/api/v1/locations/cities/?region=${encodeURIComponent(form.region)}`)
      .then((items) => {
        if (!active) return;
        setCities(items);
        setForm((current) => {
          if (current.region !== form.region || current.city) return current;
          const bamako = items.find((city) => city.name.toLowerCase() === "bamako");
          return bamako ? { ...current, city: bamako.id } : current;
        });
      })
      .catch((caught) => { if (active) setError(errorMessage(caught)); });
    return () => { active = false; };
  }, [form.region]);

  useEffect(() => {
    if (!form.category) {
      return;
    }
    let active = true;
    apiGetAll<Trade>(
      `/api/v1/catalog/trades/?category=${encodeURIComponent(form.category)}`,
    )
      .then((items) => {
        if (active) setTrades(items);
      })
      .catch((caught) => {
        if (active) setError(errorMessage(caught));
      });
    return () => {
      active = false;
    };
  }, [form.category]);

  useEffect(() => {
    if (!form.city) {
      return;
    }
    let active = true;
    apiGetAll<Commune>(
      `/api/v1/locations/communes/?city=${encodeURIComponent(form.city)}`,
    )
      .then((items) => {
        if (active) setCommunes(items);
      })
      .catch((caught) => {
        if (active) setError(errorMessage(caught));
      });
    return () => {
      active = false;
    };
  }, [form.city]);

  useEffect(() => {
    if (!form.commune) {
      return;
    }
    let active = true;
    apiGetAll<Neighborhood>(
      `/api/v1/locations/neighborhoods/?commune=${encodeURIComponent(form.commune)}`,
    )
      .then((items) => {
        if (active) setNeighborhoods(items);
      })
      .catch((caught) => {
        if (active) setError(errorMessage(caught));
      });
    return () => {
      active = false;
    };
  }, [form.commune]);

  const payload = useMemo<RequestDraftPayload>(
    () => ({
      trade: form.trade,
      neighborhood: form.neighborhood,
      title: form.title.trim(),
      description: form.description.trim(),
      address_detail: form.address_detail.trim(),
      priority: form.priority,
    }),
    [form],
  );

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => {
      const next = { ...current, [key]: value };
      if (key === "category") next.trade = "";
      if (key === "region") {
        next.city = "";
        next.commune = "";
        next.neighborhood = "";
      }
      if (key === "city") {
        next.commune = "";
        next.neighborhood = "";
      }
      if (key === "commune") next.neighborhood = "";
      return next;
    });

    if (key === "category") {
      setTrades([]);
    }
    if (key === "region") {
      setCities([]);
      setCommunes([]);
      setNeighborhoods([]);
    }
    if (key === "city") {
      setCommunes([]);
      setNeighborhoods([]);
    }
    if (key === "commune") {
      setNeighborhoods([]);
    }
    setMessage("");
    setError("");
  }

  function validate() {
    if (
      !payload.trade ||
      !payload.neighborhood ||
      !payload.title ||
      !payload.description ||
      !payload.address_detail
    ) {
      setError("Complétez tous les champs obligatoires.");
      return false;
    }
    return true;
  }

  async function saveDraftOnly() {
    setBusy(true);
    setError("");
    try {
      const base =
        draft ??
        createRequestDraft(payload, user.id, {
          category: form.category,
          region: form.region,
          city: form.city,
          commune: form.commune,
        });
      const saved = await saveRequestDraft({
        ...base,
        payload,
        context: {
          category: form.category,
          region: form.region,
          city: form.city,
          commune: form.commune,
        },
      }, user.id);
      setDraft(saved);
      setMessage("Brouillon enregistré sur cet appareil — non envoyé.");
      window.history.replaceState(
        null,
        "",
        `/client/demandes/nouvelle?draft=${saved.id}`,
      );
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (sending.current) return;
    if (!validate()) return;

    if (!user.phone_verified_at) {
      setError("Vérifiez votre numéro de téléphone avant d’envoyer une demande.");
      return;
    }

    sending.current = true;
    setBusy(true);
    setError("");
    setMessage("");

    try {
      const created = await apiMutation<ServiceRequest>(
        "/api/v1/requests/",
        "POST",
        payload,
      );

      if (draft) {
        // A local cleanup failure cannot turn a successful server creation into a retry.
        try {
          await deleteRequestDraft(draft.id, user.id);
        } catch {
          // The saved request remains authoritative; an old local draft is harmless.
        }
      }
      router.push(`/client/demandes/${created.id}`);
      router.refresh();
    } catch (caught) {
      if (caught instanceof OfflineActionError) {
        try {
          const base =
            draft ??
            createRequestDraft(payload, user.id, {
              category: form.category,
              region: form.region,
              city: form.city,
              commune: form.commune,
            });
          const saved = await saveRequestDraft({
            ...base,
            payload,
            context: {
              category: form.category,
              region: form.region,
              city: form.city,
              commune: form.commune,
            },
          }, user.id);
          setDraft(saved);
          setMessage(
            "Connexion absente : demande conservée comme brouillon non envoyé.",
          );
          window.history.replaceState(
            null,
            "",
            `/client/demandes/nouvelle?draft=${saved.id}`,
          );
        } catch (draftError) {
          setError(errorMessage(draftError));
        }
      } else {
        setError(errorMessage(caught));
      }
    } finally {
      sending.current = false;
      setBusy(false);
    }
  }

  return (
    <main>
      <section className="client-page-head">
        <div>
          <p className="page-kicker">Nouvelle demande</p>
          <h1>De quoi avez-vous besoin ?</h1>
          <p>
            Donnez les informations utiles. Votre adresse précise n’est révélée
            qu’au prestataire effectivement attribué.
          </p>
        </div>
        <Link className="button-secondary" href="/client/brouillons">
          Mes brouillons
        </Link>
      </section>

      <form className="request-form-card" onSubmit={submit}>
        <div className="request-form-intro">
          <span className="request-form-eyebrow">Votre demande, étape par étape</span>
          <h2>Décrivez votre besoin</h2>
          <p>Choisissez le métier, indiquez le quartier, puis décrivez le problème. Vous pouvez enregistrer un brouillon à tout moment.</p>
          <div className="request-form-steps" aria-label="Étapes du formulaire">
            <span>01 · Service</span><span>02 · Lieu</span><span>03 · Détails</span><span>04 · Priorité</span>
          </div>
        </div>
        {draft && (
          <div className="draft-banner">
            <strong>Brouillon local</strong>
            <span>Ce contenu n’est pas encore une demande serveur.</span>
          </div>
        )}

        <section className="form-section">
          <div className="form-section-number">1</div>
          <div className="form-section-content">
            <h2>Type de service</h2>
            <p>Choisissez la catégorie puis le métier recherché.</p>
            <div className="form-grid two">
              <label className="field">
                <span>Catégorie *</span>
                <select
                  disabled={loadingOptions}
                  required
                  value={form.category}
                  onChange={(event) => update("category", event.target.value)}
                >
                  <option value="">Choisir une catégorie</option>
                  {categories.map((category) => (
                    <option value={category.id} key={category.id}>
                      {category.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Métier *</span>
                <select
                  disabled={!form.category}
                  required
                  value={form.trade}
                  onChange={(event) => update("trade", event.target.value)}
                >
                  <option value="">Choisir un métier</option>
                  {trades.map((trade) => (
                    <option value={trade.id} key={trade.id}>
                      {trade.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </div>
        </section>

        <section className="form-section">
          <div className="form-section-number">2</div>
          <div className="form-section-content">
            <h2>Lieu de l’intervention</h2>
            <p>Sélectionnez votre zone puis précisez l’adresse.</p>
            <div className="form-grid two">
              <label className="field">
                <span>Région / district *</span>
                <select required value={form.region} onChange={(event) => update("region", event.target.value)}>
                  <option value="">Choisir</option>
                  {regions.map((region) => (
                    <option value={region.id} key={region.id}>{region.name}</option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Ville *</span>
                <select
                  disabled={!form.region}
                  required
                  value={form.city}
                  onChange={(event) => update("city", event.target.value)}
                >
                  <option value="">Choisir</option>
                  {cities.map((city) => (
                    <option value={city.id} key={city.id}>
                      {city.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Commune *</span>
                <select
                  disabled={!form.city}
                  required
                  value={form.commune}
                  onChange={(event) => update("commune", event.target.value)}
                >
                  <option value="">Choisir</option>
                  {communes.map((commune) => (
                    <option value={commune.id} key={commune.id}>
                      {commune.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Quartier *</span>
                <select
                  disabled={!form.commune}
                  required
                  value={form.neighborhood}
                  onChange={(event) => update("neighborhood", event.target.value)}
                >
                  <option value="">Choisir</option>
                  {neighborhoods.map((neighborhood) => (
                    <option value={neighborhood.id} key={neighborhood.id}>
                      {neighborhood.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <label className="field">
              <span>Adresse / repère précis *</span>
              <input
                maxLength={250}
                required
                placeholder="Ex. porte bleue, près de la pharmacie…"
                value={form.address_detail}
                onChange={(event) => update("address_detail", event.target.value)}
              />
              <small>
                Visible par le prestataire seulement après attribution.
              </small>
            </label>
          </div>
        </section>

        <section className="form-section">
          <div className="form-section-number">3</div>
          <div className="form-section-content">
            <h2>Décrivez le problème</h2>
            <div className="form-stack">
              <label className="field">
                <span>Titre *</span>
                <input
                  maxLength={150}
                  required
                  placeholder="Ex. climatiseur ne démarre plus"
                  value={form.title}
                  onChange={(event) => update("title", event.target.value)}
                />
                <small className="field-count">{form.title.length}/150 caractères</small>
              </label>
              <label className="field">
                <span>Description *</span>
                <textarea
                  maxLength={2000}
                  required
                  rows={6}
                  placeholder="Expliquez ce qui se passe, depuis quand, et les détails utiles…"
                  value={form.description}
                  onChange={(event) => update("description", event.target.value)}
                />
                <small className="field-count">{form.description.length}/2000 caractères</small>
              </label>
            </div>
          </div>
        </section>

        <section className="form-section">
          <div className="form-section-number">4</div>
          <div className="form-section-content">
            <h2>Priorité</h2>
            <div className="priority-grid">
              <label
                className={
                  form.priority === "NORMAL"
                    ? "priority-option active"
                    : "priority-option"
                }
              >
                <input
                  checked={form.priority === "NORMAL"}
                  name="priority"
                  type="radio"
                  value="NORMAL"
                  onChange={() => update("priority", "NORMAL")}
                />
                <strong>Normale</strong>
                <span>Demande standard.</span>
              </label>
              <label
                className={
                  form.priority === "URGENT"
                    ? "priority-option urgent active"
                    : "priority-option urgent"
                }
              >
                <input
                  checked={form.priority === "URGENT"}
                  name="priority"
                  type="radio"
                  value="URGENT"
                  onChange={() => update("priority", "URGENT")}
                />
                <strong>Urgente</strong>
                <span>Recherche rapide parmi les prestataires compatibles.</span>
              </label>
            </div>
          </div>
        </section>

        {message && <p className="form-success" role="status">{message}</p>}
        {error && <p className="form-error" role="alert">{error}</p>}

        <div className="form-actions">
          <button
            className="button-secondary"
            disabled={busy}
            type="button"
            onClick={saveDraftOnly}
          >
            Enregistrer comme brouillon
          </button>
          <button
            className="button-primary"
            disabled={busy || !user.phone_verified_at}
            type="submit"
          >
            {busy ? "Traitement…" : "Envoyer la demande"}
          </button>
        </div>

        {!user.phone_verified_at && (
          <p className="form-note">
            <Link href="/client/profil">Vérifiez votre téléphone</Link> pour
            pouvoir envoyer la demande. Vous pouvez déjà enregistrer un brouillon.
          </p>
        )}
      </form>
    </main>
  );
}
