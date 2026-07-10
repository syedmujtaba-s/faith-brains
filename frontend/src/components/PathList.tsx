"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
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

  useEffect(() => {
    fetch("/api/v1/learn/paths", { headers: sessionHeaders() })
      .then((r) => (r.ok ? r.json() : []))
      .then(setPaths)
      .catch(() => setPaths([]));
  }, []);

  if (paths === null) {
    return <p className="text-sm text-mist">Loading paths…</p>;
  }
  if (paths.length === 0) return null;

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {paths.map((p) => {
        const pct = p.step_count ? Math.round((p.completed_count / p.step_count) * 100) : 0;
        return (
          <Link
            key={p.key}
            href={`/learn/${p.key}`}
            className="block rounded-lg border border-line bg-lapis p-5 transition-colors hover:border-gold/50 hover:bg-raise"
          >
            <h3 className="font-display text-lg text-snow">{p.title}</h3>
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
