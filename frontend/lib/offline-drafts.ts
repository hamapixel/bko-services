export type RequestDraftPayload = {
  trade: string;
  neighborhood: string;
  title: string;
  description: string;
  address_detail: string;
  priority: "NORMAL" | "URGENT";
};

export type RequestDraftContext = {
  category?: string;
  region?: string;
  city?: string;
  commune?: string;
};

export type RequestDraft = {
  id: string;
  kind: "SERVICE_REQUEST";
  state: "LOCAL_DRAFT";
  payload: RequestDraftPayload;
  context?: RequestDraftContext;
  createdAt: string;
  updatedAt: string;
};

const DATABASE_NAME = "bko-services";
const DATABASE_VERSION = 1;
const STORE_NAME = "request-drafts";

function ensureBrowser() {
  if (typeof window === "undefined" || !("indexedDB" in window)) {
    throw new Error("Le stockage de brouillons n'est pas disponible.");
  }
}

function openDatabase(): Promise<IDBDatabase> {
  ensureBrowser();

  return new Promise((resolve, reject) => {
    const request = window.indexedDB.open(DATABASE_NAME, DATABASE_VERSION);

    request.onupgradeneeded = () => {
      const database = request.result;
      if (!database.objectStoreNames.contains(STORE_NAME)) {
        database.createObjectStore(STORE_NAME, { keyPath: "id" });
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () =>
      reject(request.error ?? new Error("Impossible d'ouvrir les brouillons."));
  });
}

function transactionDone(transaction: IDBTransaction): Promise<void> {
  return new Promise((resolve, reject) => {
    transaction.oncomplete = () => resolve();
    transaction.onerror = () =>
      reject(transaction.error ?? new Error("Échec du stockage local."));
    transaction.onabort = () =>
      reject(transaction.error ?? new Error("Stockage local annulé."));
  });
}

export function createRequestDraft(
  payload: RequestDraftPayload,
  context?: RequestDraftContext,
): RequestDraft {
  const now = new Date().toISOString();

  return {
    id: crypto.randomUUID(),
    kind: "SERVICE_REQUEST",
    state: "LOCAL_DRAFT",
    payload,
    context,
    createdAt: now,
    updatedAt: now,
  };
}

export async function saveRequestDraft(
  draft: RequestDraft,
): Promise<RequestDraft> {
  const database = await openDatabase();
  const updated: RequestDraft = {
    ...draft,
    state: "LOCAL_DRAFT",
    updatedAt: new Date().toISOString(),
  };

  const transaction = database.transaction(STORE_NAME, "readwrite");
  transaction.objectStore(STORE_NAME).put(updated);
  await transactionDone(transaction);
  database.close();
  return updated;
}

export async function listRequestDrafts(): Promise<RequestDraft[]> {
  const database = await openDatabase();

  const drafts = await new Promise<RequestDraft[]>((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, "readonly");
    const request = transaction.objectStore(STORE_NAME).getAll();

    request.onsuccess = () => {
      resolve(
        (request.result as RequestDraft[]).sort((left, right) =>
          right.updatedAt.localeCompare(left.updatedAt),
        ),
      );
    };
    request.onerror = () =>
      reject(request.error ?? new Error("Impossible de lire les brouillons."));
  });

  database.close();
  return drafts;
}

export async function getRequestDraft(
  id: string,
): Promise<RequestDraft | null> {
  const database = await openDatabase();

  const draft = await new Promise<RequestDraft | null>((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, "readonly");
    const request = transaction.objectStore(STORE_NAME).get(id);

    request.onsuccess = () =>
      resolve((request.result as RequestDraft | undefined) ?? null);
    request.onerror = () =>
      reject(request.error ?? new Error("Impossible de lire le brouillon."));
  });

  database.close();
  return draft;
}

export async function deleteRequestDraft(id: string): Promise<void> {
  const database = await openDatabase();
  const transaction = database.transaction(STORE_NAME, "readwrite");
  transaction.objectStore(STORE_NAME).delete(id);
  await transactionDone(transaction);
  database.close();
}
