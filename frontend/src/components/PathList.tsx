"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { Persona } from "@/lib/api";
import { loadPersona } from "@/lib/persona";
import { sessionHeaders } from "@/lib/session";

type PathSummary = {
  key: string;
  title: string;
  description: string;
  step_count: number;
  completed_count: number;
};

export default function PathList() {
  const [paths, setPaths] = useState<PathSummary[] | null>(null);
  const [recommended, setRecommended] = useState<Set<string>>(new Set());

  useEffect(() => {
    fetch("/api/v1/learn/paths", { headers: sessionHeaders() })
      .then((r) => (r.ok ? r.json() : []))
      .then(setPaths)
      .catch(() => setPaths([]));

    const persona = loadPersona();
    if (persona) {
      fetch("/api/v1/personas")
        .then((r) => (r.ok ? r.json() : []))
        .then((personas: Persona[]) => {
          const active = personas.find((p) => p.key === persona);
          if (active) setRecommended(new Set(active.recommended_paths));
        })
        .catch(() => {});
    }
  }, []);

  if (paths === null) {
    return <p className="text-sm text-mist">Loading paths…</p>;
  }
  if (paths.length === 0) return null;

  // Recommended paths first; original order preserved within each group
  const ordered = [...paths].sort(
    (a, b) => Number(recommended.has(b.key)) - Number(recommended.has(a.key))
  );

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {ordered.map((p) => {
        const pct = p.step_count ? Math.round((p.completed_count / p.step_count) * 100) : 0;
        return (
          <Link
            key={p.key}
            href={`/learn/${p.key}`}
            className="block rounded-lg border border-line bg-lapis p-5 transition-colors hover:border-gold/50 hover:bg-raise"
          >
            <div className="flex items-start justify-between gap-2">
              <h3 className="font-display text-lg text-snow">{p.title}</h3>
              {recommended.has(p.key) && (
                <span className="mt-1 shrink-0 rounded-full border border-gold/40 px-2 py-0.5 text-[10px] tracking-wide text-goldsoft">
                  Recommended for you
                </span>
              )}
            </div>
            <p className="mt-1 text-sm leading-relaxed text-mist">{p.description}</p>
            <div className="mt-4">
              <div className="h-1.5 overflow-hidden rounded-full bg-ink">
                <div className="h-full rounded-full bg-gold" style={{ width: `${pct}%` }} />
              </div>
              <p className="mt-1.5 text-xs text-mist/80">
                {p.completed_count}/{p.step_count} studied
              </p>
            </div>
          </Link>
        );
      })}
    </div>
  );
}
