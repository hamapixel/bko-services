"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";

import { apiGet, apiMutation } from "@/lib/admin-api";

type AdminCategory = {
  id: string;
  name: string;
  description: string;
  display_order: number;
  is_active: boolean;
};

type AdminTrade = {
  id: string;
  category: string;
  category_name: string;
  name: string;
  description: string;
  display_order: number;
  is_active: boolean;
};

type CategoryForm = {
  name: string;
  description: string;
  display_order: string;
  is_active: boolean;
};

type TradeForm = {
  category: string;
  name: string;
  description: string;
  display_order: string;
  is_active: boolean;
};

const EMPTY_CATEGORY: CategoryForm = {
  name: "",
  description: "",
  display_order: "0",
  is_active: true,
};

const EMPTY_TRADE: TradeForm = {
  category: "",
  name: "",
  description: "",
  display_order: "0",
  is_active: true,
};

const fieldStyle = {
  display: "grid",
  gap: 7,
} as const;

const inputStyle = {
  width: "100%",
  minHeight: 44,
  padding: "10px 12px",
  border: "1px solid #d8e1ea",
  borderRadius: 12,
  background: "#fff",
  color: "#142033",
} as const;

export default function AdminCataloguePage() {
  const [categories, setCategories] = useState<AdminCategory[]>([]);
  const [trades, setTrades] = useState<AdminTrade[]>([]);
  const [categoryForm, setCategoryForm] = useState<CategoryForm>(EMPTY_CATEGORY);
  const [tradeForm, setTradeForm] = useState<TradeForm>(EMPTY_TRADE);
  const [editingCategoryId, setEditingCategoryId] = useState<string | null>(null);
  const [editingTradeId, setEditingTradeId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function refreshData() {
    const [categoryRows, tradeRows] = await Promise.all([
      apiGet<AdminCategory[]>("/api/v1/admin/catalog/categories/"),
      apiGet<AdminTrade[]>("/api/v1/admin/catalog/trades/"),
    ]);
    setCategories(categoryRows);
    setTrades(tradeRows);
    setTradeForm((current) => ({
      ...current,
      category: current.category || categoryRows[0]?.id || "",
    }));
  }

  useEffect(() => {
    let active = true;
    Promise.all([
      apiGet<AdminCategory[]>("/api/v1/admin/catalog/categories/"),
      apiGet<AdminTrade[]>("/api/v1/admin/catalog/trades/"),
    ])
      .then(([categoryRows, tradeRows]) => {
        if (!active) return;
        setCategories(categoryRows);
        setTrades(tradeRows);
        setTradeForm((current) => ({
          ...current,
          category: current.category || categoryRows[0]?.id || "",
        }));
      })
      .catch((caught) => {
        if (!active) return;
        setError(
          caught instanceof Error
            ? caught.message
            : "Impossible de charger le catalogue.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const normalizedQuery = query.trim().toLocaleLowerCase("fr");
  const filteredCategories = useMemo(
    () => categories.filter((category) =>
      !normalizedQuery
      || category.name.toLocaleLowerCase("fr").includes(normalizedQuery)
      || category.description.toLocaleLowerCase("fr").includes(normalizedQuery),
    ),
    [categories, normalizedQuery],
  );
  const filteredTrades = useMemo(
    () => trades.filter((trade) =>
      !normalizedQuery
      || trade.name.toLocaleLowerCase("fr").includes(normalizedQuery)
      || trade.category_name.toLocaleLowerCase("fr").includes(normalizedQuery)
      || trade.description.toLocaleLowerCase("fr").includes(normalizedQuery),
    ),
    [normalizedQuery, trades],
  );

  function resetCategoryForm() {
    setEditingCategoryId(null);
    setCategoryForm(EMPTY_CATEGORY);
  }

  function resetTradeForm() {
    setEditingTradeId(null);
    setTradeForm({ ...EMPTY_TRADE, category: categories[0]?.id || "" });
  }

  function editCategory(category: AdminCategory) {
    setEditingCategoryId(category.id);
    setCategoryForm({
      name: category.name,
      description: category.description,
      display_order: String(category.display_order),
      is_active: category.is_active,
    });
    document.getElementById("category-editor")?.scrollIntoView({ behavior: "smooth" });
  }

  function editTrade(trade: AdminTrade) {
    setEditingTradeId(trade.id);
    setTradeForm({
      category: trade.category,
      name: trade.name,
      description: trade.description,
      display_order: String(trade.display_order),
      is_active: trade.is_active,
    });
    document.getElementById("trade-editor")?.scrollIntoView({ behavior: "smooth" });
  }

  async function saveCategory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const order = Number(categoryForm.display_order);
    if (!categoryForm.name.trim()) {
      setError("Le nom de la catégorie est obligatoire.");
      return;
    }
    if (!Number.isInteger(order) || order < 0 || order > 32767) {
      setError("L’ordre d’affichage doit être un entier entre 0 et 32767.");
      return;
    }

    setBusy(true);
    setError("");
    setMessage("");
    try {
      await apiMutation(
        editingCategoryId
          ? `/api/v1/admin/catalog/categories/${editingCategoryId}/`
          : "/api/v1/admin/catalog/categories/",
        editingCategoryId ? "PATCH" : "POST",
        {
          name: categoryForm.name.trim(),
          description: categoryForm.description.trim(),
          display_order: order,
          is_active: categoryForm.is_active,
        },
      );
      await refreshData();
      resetCategoryForm();
      setMessage(
        editingCategoryId
          ? "Catégorie mise à jour."
          : "Catégorie ajoutée au catalogue BKO Services.",
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Enregistrement impossible.");
    } finally {
      setBusy(false);
    }
  }

  async function saveTrade(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const order = Number(tradeForm.display_order);
    if (!tradeForm.category) {
      setError("Choisissez une catégorie pour ce métier.");
      return;
    }
    if (!tradeForm.name.trim()) {
      setError("Le nom du métier est obligatoire.");
      return;
    }
    if (!Number.isInteger(order) || order < 0 || order > 32767) {
      setError("L’ordre d’affichage doit être un entier entre 0 et 32767.");
      return;
    }

    setBusy(true);
    setError("");
    setMessage("");
    try {
      await apiMutation(
        editingTradeId
          ? `/api/v1/admin/catalog/trades/${editingTradeId}/`
          : "/api/v1/admin/catalog/trades/",
        editingTradeId ? "PATCH" : "POST",
        {
          category: tradeForm.category,
          name: tradeForm.name.trim(),
          description: tradeForm.description.trim(),
          display_order: order,
          is_active: tradeForm.is_active,
        },
      );
      await refreshData();
      resetTradeForm();
      setMessage(
        editingTradeId
          ? "Métier mis à jour."
          : "Métier ajouté au catalogue BKO Services.",
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Enregistrement impossible.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleCategory(category: AdminCategory) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await apiMutation(
        `/api/v1/admin/catalog/categories/${category.id}/`,
        "PATCH",
        { is_active: !category.is_active },
      );
      await refreshData();
      setMessage(
        category.is_active
          ? "Catégorie désactivée. Ses métiers ne sont plus proposés aux nouveaux utilisateurs."
          : "Catégorie réactivée.",
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Mise à jour impossible.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleTrade(trade: AdminTrade) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await apiMutation(
        `/api/v1/admin/catalog/trades/${trade.id}/`,
        "PATCH",
        { is_active: !trade.is_active },
      );
      await refreshData();
      setMessage(trade.is_active ? "Métier désactivé." : "Métier réactivé.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Mise à jour impossible.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <section className="admin-page-head">
        <div>
          <p className="page-kicker">Catalogue</p>
          <h1>Catégories & métiers</h1>
          <p>
            Ajoutez les services proposés sur BKO Services sans passer par Django Admin.
            Un élément désactivé reste dans l’historique mais n’est plus proposé aux nouveaux parcours.
          </p>
        </div>
      </section>

      {message && <div className="form-success">{message}</div>}
      {error && <div className="inline-error">{error}</div>}
      {loading && <div className="skeleton-list">Chargement…</div>}

      {!loading && (
        <>
          <section
            className="detail-card admin-section-gap"
            style={{ display: "grid", gap: 16 }}
          >
            <div>
              <p className="page-kicker">Recherche</p>
              <h2>Retrouver rapidement un service</h2>
            </div>
            <input
              style={inputStyle}
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Ex. maquillage, plomberie, bâtiment…"
              aria-label="Rechercher une catégorie ou un métier"
            />
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
              <span className="status-pill success">{categories.length} catégorie(s)</span>
              <span className="status-pill active">{trades.length} métier(s)</span>
            </div>
          </section>

          <section
            id="category-editor"
            className="detail-card admin-section-gap"
            style={{ display: "grid", gap: 18 }}
          >
            <div>
              <p className="page-kicker">Catégories</p>
              <h2>{editingCategoryId ? "Modifier la catégorie" : "Ajouter une catégorie"}</h2>
              <p>Exemples : Beauté, Bâtiment, Maison, Informatique, Auto & Moto.</p>
            </div>

            <form onSubmit={saveCategory} style={{ display: "grid", gap: 14 }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 14 }}>
                <label style={fieldStyle}>
                  <strong>Nom *</strong>
                  <input
                    style={inputStyle}
                    value={categoryForm.name}
                    onChange={(event) => setCategoryForm((current) => ({ ...current, name: event.target.value }))}
                    maxLength={120}
                    placeholder="Beauté"
                    required
                  />
                </label>
                <label style={fieldStyle}>
                  <strong>Ordre d’affichage</strong>
                  <input
                    style={inputStyle}
                    type="number"
                    min="0"
                    max="32767"
                    value={categoryForm.display_order}
                    onChange={(event) => setCategoryForm((current) => ({ ...current, display_order: event.target.value }))}
                  />
                </label>
              </div>
              <label style={fieldStyle}>
                <strong>Description</strong>
                <textarea
                  style={{ ...inputStyle, minHeight: 90, resize: "vertical" }}
                  value={categoryForm.description}
                  onChange={(event) => setCategoryForm((current) => ({ ...current, description: event.target.value }))}
                  placeholder="Décrivez les services regroupés dans cette catégorie."
                />
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <input
                  type="checkbox"
                  checked={categoryForm.is_active}
                  onChange={(event) => setCategoryForm((current) => ({ ...current, is_active: event.target.checked }))}
                />
                <span>Catégorie active et visible dans les nouveaux parcours</span>
              </label>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                <button className="button-primary" type="submit" disabled={busy}>
                  {busy ? "Enregistrement…" : editingCategoryId ? "Enregistrer les modifications" : "+ Ajouter la catégorie"}
                </button>
                {editingCategoryId && (
                  <button className="button-secondary" type="button" onClick={resetCategoryForm} disabled={busy}>
                    Annuler
                  </button>
                )}
              </div>
            </form>

            <div style={{ display: "grid", gap: 10 }}>
              {filteredCategories.map((category) => (
                <article
                  key={category.id}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "minmax(180px, 1fr) auto",
                    gap: 12,
                    alignItems: "center",
                    padding: 14,
                    border: "1px solid #e3e9ef",
                    borderRadius: 14,
                  }}
                >
                  <div>
                    <strong>{category.name}</strong>
                    <p style={{ margin: "5px 0 0" }}>{category.description || "Aucune description"}</p>
                    <small>Ordre {category.display_order} · {category.is_active ? "Active" : "Inactive"}</small>
                  </div>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
                    <button className="button-secondary" type="button" onClick={() => editCategory(category)} disabled={busy}>
                      Modifier
                    </button>
                    <button className="button-secondary" type="button" onClick={() => void toggleCategory(category)} disabled={busy}>
                      {category.is_active ? "Désactiver" : "Activer"}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section
            id="trade-editor"
            className="detail-card admin-section-gap"
            style={{ display: "grid", gap: 18 }}
          >
            <div>
              <p className="page-kicker">Métiers</p>
              <h2>{editingTradeId ? "Modifier le métier" : "Ajouter un métier"}</h2>
              <p>Exemples : Maquillage, Terrassement, Carreleur, Soudeur, Réparateur téléphone.</p>
            </div>

            {categories.length === 0 ? (
              <div className="inline-error">Créez d’abord au moins une catégorie.</div>
            ) : (
              <form onSubmit={saveTrade} style={{ display: "grid", gap: 14 }}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 14 }}>
                  <label style={fieldStyle}>
                    <strong>Catégorie *</strong>
                    <select
                      style={inputStyle}
                      value={tradeForm.category}
                      onChange={(event) => setTradeForm((current) => ({ ...current, category: event.target.value }))}
                      required
                    >
                      {categories.map((category) => (
                        <option key={category.id} value={category.id}>
                          {category.name}{category.is_active ? "" : " — inactive"}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label style={fieldStyle}>
                    <strong>Nom du métier *</strong>
                    <input
                      style={inputStyle}
                      value={tradeForm.name}
                      onChange={(event) => setTradeForm((current) => ({ ...current, name: event.target.value }))}
                      maxLength={120}
                      placeholder="Maquillage"
                      required
                    />
                  </label>
                  <label style={fieldStyle}>
                    <strong>Ordre d’affichage</strong>
                    <input
                      style={inputStyle}
                      type="number"
                      min="0"
                      max="32767"
                      value={tradeForm.display_order}
                      onChange={(event) => setTradeForm((current) => ({ ...current, display_order: event.target.value }))}
                    />
                  </label>
                </div>
                <label style={fieldStyle}>
                  <strong>Description</strong>
                  <textarea
                    style={{ ...inputStyle, minHeight: 90, resize: "vertical" }}
                    value={tradeForm.description}
                    onChange={(event) => setTradeForm((current) => ({ ...current, description: event.target.value }))}
                    placeholder="Décrivez ce service."
                  />
                </label>
                <label style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <input
                    type="checkbox"
                    checked={tradeForm.is_active}
                    onChange={(event) => setTradeForm((current) => ({ ...current, is_active: event.target.checked }))}
                  />
                  <span>Métier actif et sélectionnable par les clients et prestataires</span>
                </label>
                <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                  <button className="button-primary" type="submit" disabled={busy}>
                    {busy ? "Enregistrement…" : editingTradeId ? "Enregistrer les modifications" : "+ Ajouter le métier"}
                  </button>
                  {editingTradeId && (
                    <button className="button-secondary" type="button" onClick={resetTradeForm} disabled={busy}>
                      Annuler
                    </button>
                  )}
                </div>
              </form>
            )}

            <div style={{ display: "grid", gap: 10 }}>
              {filteredTrades.map((trade) => (
                <article
                  key={trade.id}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "minmax(180px, 1fr) auto",
                    gap: 12,
                    alignItems: "center",
                    padding: 14,
                    border: "1px solid #e3e9ef",
                    borderRadius: 14,
                  }}
                >
                  <div>
                    <strong>{trade.name}</strong>
                    <p style={{ margin: "5px 0 0" }}>{trade.category_name} · {trade.description || "Aucune description"}</p>
                    <small>Ordre {trade.display_order} · {trade.is_active ? "Actif" : "Inactif"}</small>
                  </div>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
                    <button className="button-secondary" type="button" onClick={() => editTrade(trade)} disabled={busy}>
                      Modifier
                    </button>
                    <button className="button-secondary" type="button" onClick={() => void toggleTrade(trade)} disabled={busy}>
                      {trade.is_active ? "Désactiver" : "Activer"}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </section>
        </>
      )}
    </main>
  );
}
