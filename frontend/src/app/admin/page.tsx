"use client";

import { useCallback, useEffect, useState } from "react";

type Stats = {
  verses: number;
  hadiths: number;
  quran_embeddings: number;
  hadith_embeddings: number;
  asks_total: number;
  asks_by_category: Record<string, number>;
  asks_errored: number;
  avg_latency_ms: number | null;
};

type AskLog = {
  id: number;
  created_at: string;
  question: string;
  category: string | null;
  answer: string | null;
  provider: string | null;
  model: string | null;
  latency_ms: number | null;
  status: string;
  error: string | null;
};

function Tile({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg border border-line bg-lapis p-4">
      <p className="text-xs tracking-wide text-mist">{label}</p>
      <p className="font-display mt-1 text-2xl text-goldsoft">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-mist">{sub}</p>}
    </div>
  );
}

export default function AdminPage() {
  const [token, setToken] = useState("");
  const [authed, setAuthed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [asks, setAsks] = useState<AskLog[]>([]);

  const load = useCallback(async (tok: string) => {
    setError(null);
    const headers = { "X-Admin-Token": tok };
    const [statsRes, asksRes] = await Promise.all([
      fetch("/api/v1/admin/stats", { headers }),
      fetch("/api/v1/admin/asks?limit=50", { headers }),
    ]);
    if (!statsRes.ok) {
      const body = await statsRes.json().catch(() => null);
      setAuthed(false);
      setError(body?.detail ?? `Error ${statsRes.status}`);
      return;
    }
    setStats(await statsRes.json());
    setAsks((await asksRes.json()).items ?? []);
    setAuthed(true);
    sessionStorage.setItem("fb-admin-token", tok);
  }, []);

  useEffect(() => {
    const stored = sessionStorage.getItem("fb-admin-token");
    if (stored) {
      setToken(stored);
      void load(stored);
    }
  }, [load]);

  if (!authed) {
    return (
      <div className="mx-auto max-w-sm pt-16">
        <h1 className="font-display mb-4 text-center text-2xl text-snow">Admin</h1>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void load(token);
          }}
          className="space-y-3"
        >
          <input
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="ADMIN_TOKEN from .env"
            className="w-full rounded-lg border border-line bg-lapis px-4 py-2.5 text-snow placeholder:text-mist/60"
          />
          <button type="submit" className="w-full rounded-lg bg-gold py-2.5 text-sm font-bold text-ink">
            Open dashboard
          </button>
          {error && <p className="text-center text-sm text-[#e8a9a0]">{error}</p>}
        </form>
      </div>
    );
  }

  return (
    <div>
      <h1 className="font-display mb-6 text-3xl text-snow">Admin</h1>

      {stats && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Tile label="Verses" value={stats.verses.toLocaleString()} />
          <Tile label="Hadith" value={stats.hadiths.toLocaleString()} />
          <Tile
            label="Quran embeddings"
            value={`${Math.round((stats.quran_embeddings / Math.max(stats.verses, 1)) * 100)}%`}
            sub={`${stats.quran_embeddings.toLocaleString()} embedded`}
          />
          <Tile
            label="Hadith embeddings"
            value={`${Math.round((stats.hadith_embeddings / Math.max(stats.hadiths, 1)) * 100)}%`}
            sub={`${stats.hadith_embeddings.toLocaleString()} embedded`}
          />
          <Tile label="Questions asked" value={stats.asks_total.toLocaleString()} />
          <Tile label="Errors" value={stats.asks_errored.toLocaleString()} />
          <Tile
            label="Avg answer time"
            value={stats.avg_latency_ms ? `${(stats.avg_latency_ms / 1000).toFixed(1)}s` : "—"}
          />
          <Tile
            label="By category"
            value={String(Object.values(stats.asks_by_category).reduce((a, b) => a + b, 0))}
            sub={Object.entries(stats.asks_by_category)
              .map(([k, v]) => `${k}: ${v}`)
              .join(" · ")}
          />
        </div>
      )}

      <h2 className="font-display mt-10 mb-3 text-lg text-goldsoft">Recent questions</h2>
      <div className="space-y-3">
        {asks.length === 0 && <p className="text-sm text-mist">No questions logged yet.</p>}
        {asks.map((a) => (
          <details key={a.id} className="rounded-lg border border-line bg-lapis p-4">
            <summary className="cursor-pointer text-sm text-snow">
              <span className={a.status === "error" ? "text-[#e8a9a0]" : "text-goldsoft"}>
                [{a.status === "error" ? "error" : a.category}]
              </span>{" "}
              {a.question}
              <span className="float-right text-xs text-mist">
                {new Date(a.created_at).toLocaleString()} ·{" "}
                {a.latency_ms != null ? `${(a.latency_ms / 1000).toFixed(1)}s` : "—"}
              </span>
            </summary>
            <div className="mt-3 border-t border-line pt-3 text-sm leading-relaxed text-snow/85">
              {a.error ? <p className="text-[#e8a9a0]">{a.error}</p> : <p>{a.answer}</p>}
              <p className="mt-2 text-xs text-mist">
                {a.provider} · {a.model}
              </p>
            </div>
          </details>
        ))}
      </div>
    </div>
  );
}
