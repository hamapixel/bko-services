"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { apiGetAll, type Trade } from "@/lib/client-api";

function normalized(value: string) {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("fr");
}

export default function ServiceSearch() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    apiGetAll<Trade>("/api/v1/catalog/trades/")
      .then((items) => { if (active) setTrades(items); })
      .catch(() => { if (active) setError(true); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const matches = useMemo(() => {
    const value = normalized(query.trim());
    if (!value) return [];
    return trades.filter((trade) => normalized(trade.name).includes(value)).slice(0, 6);
  }, [query, trades]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (matches[0]) router.push(`/client/demandes/nouvelle?trade=${matches[0].id}`);
  }

  return (
    <div className="home-service-search">
      <form onSubmit={submit} role="search">
        <label htmlFor="home-trade-search">Quel professionnel recherchez-vous ?</label>
        <div className="home-service-search-row">
          <input
            id="home-trade-search"
            type="search"
            autoComplete="off"
            placeholder="Ex. plombier, électricien…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <button type="submit" disabled={!matches.length}>Rechercher</button>
        </div>
      </form>
      {query.trim() && (
        <div className="home-service-results" aria-live="polite">
          {loading ? <p>Recherche des métiers…</p> : error ? (
            <p>Recherche indisponible pour le moment.</p>
          ) : matches.length ? (
            <ul aria-label="Métiers correspondants">
              {matches.map((trade) => (
                <li key={trade.id}>
                  <Link href={`/client/demandes/nouvelle?trade=${trade.id}`}>{trade.name}<span aria-hidden="true">↗</span></Link>
                </li>
              ))}
            </ul>
          ) : <p>Aucun métier trouvé. Essayez un autre terme.</p>}
        </div>
      )}
    </div>
  );
}
