"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  deleteRequestDraft,
  listRequestDrafts,
  type RequestDraft,
} from "@/lib/offline-drafts";

function localDate(value: string) {
  return new Intl.DateTimeFormat("fr-ML", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function ClientDraftsPage() {
  const [drafts, setDrafts] = useState<RequestDraft[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    listRequestDrafts()
      .then((items) => {
        if (!active) return;
        setDrafts(items);
        setError("");
      })
      .catch((caught) => {
        if (!active) return;
        setError(
          caught instanceof Error
            ? caught.message
            : "Impossible de lire les brouillons.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  async function refreshAfterMutation() {
    try {
      setDrafts(await listRequestDrafts());
      setError("");
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Impossible de lire les brouillons.",
      );
    }
  }

  async function removeDraft(id: string) {
    if (!window.confirm("Supprimer ce brouillon de cet appareil ?")) {
      return;
    }
    await deleteRequestDraft(id);
    await refreshAfterMutation();
  }

  return (
    <main>
      <section className="client-page-head">
        <div>
          <p className="page-kicker">Hors connexion</p>
          <h1>Mes brouillons</h1>
          <p>
            Ces éléments sont stockés uniquement sur cet appareil et ne sont
            pas des demandes envoyées.
          </p>
        </div>
        <Link className="button-primary" href="/client/demandes/nouvelle">
          + Nouveau brouillon
        </Link>
      </section>

      <div className="draft-safety-note">
        <strong>Important :</strong> le badge « Brouillon local » signifie que
        BKO Services n’a encore rien reçu côté serveur.
      </div>

      {loading && <div className="skeleton-list">Lecture des brouillons…</div>}
      {error && <div className="inline-error">{error}</div>}

      {!loading && !error && drafts.length === 0 && (
        <div className="empty-state">
          <strong>Aucun brouillon local</strong>
          <p>
            Si votre connexion coupe pendant une saisie, vous pourrez conserver
            la demande ici sans la déclarer envoyée.
          </p>
        </div>
      )}

      <div className="draft-list">
        {drafts.map((draft) => (
          <article className="draft-card" key={draft.id}>
            <div className="draft-card-main">
              <span className="draft-state">Brouillon local · non envoyé</span>
              <h3>{draft.payload.title || "Demande sans titre"}</h3>
              <p>
                {draft.payload.description || "Description à compléter."}
              </p>
              <div className="request-card-details">
                <span>
                  {draft.payload.priority === "URGENT" ? "⚡ Urgente" : "Normale"}
                </span>
                <span>Modifié {localDate(draft.updatedAt)}</span>
              </div>
            </div>
            <div className="draft-card-actions">
              <Link
                className="button-primary"
                href={`/client/demandes/nouvelle?draft=${draft.id}`}
              >
                Reprendre
              </Link>
              <button
                className="button-danger-ghost"
                type="button"
                onClick={() => removeDraft(draft.id)}
              >
                Supprimer
              </button>
            </div>
          </article>
        ))}
      </div>
    </main>
  );
}
