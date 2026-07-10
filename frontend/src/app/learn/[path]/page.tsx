"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { sessionHeaders } from "@/lib/session";

type Step = {
  key: string;
  title: string;
  kind: "quran" | "hadith";
  reference: string;
  arabic: string | null;
  text: string | null;
  grading: string | null;
  completed: boolean;
};

type PathDetail = { key: string; title: string; description: string; steps: Step[] };

export default function PathPage({ params }: { params: Promise<{ path: string }> }) {
  const { path } = use(params);
  const [detail, setDetail] = useState<PathDetail | null>(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    fetch(`/api/v1/learn/paths/${path}`, { headers: sessionHeaders() })
      .then(async (r) => (r.ok ? setDetail(await r.json()) : setMissing(true)))
      .catch(() => setMissing(true));
  }, [path]);

  async function markStudied(step: Step) {
    if (!detail || step.completed) return;
    setDetail({
      ...detail,
      steps: detail.steps.map((s) => (s.key === step.key ? { ...s, completed: true } : s)),
    });
    fetch(`/api/v1/learn/paths/${path}/steps/${step.key}/complete`, {
      method: "POST",
      headers: sessionHeaders(),
    }).catch(() => {});
  }

  if (missing) {
    return (
      <div className="mx-auto max-w-3xl text-center">
        <p className="text-mist">This learning path doesn&apos;t exist.</p>
        <Link href="/learn" className="text-goldsoft underline underline-offset-4">
          Back to Learn
        </Link>
      </div>
    );
  }
  if (!detail) return <p className="mx-auto max-w-3xl text-sm text-mist">Loading path…</p>;

  const done = detail.steps.filter((s) => s.completed).length;

  return (
    <div className="mx-auto max-w-3xl">
      <Link href="/learn" className="text-xs text-mist hover:text-goldsoft">
        ← Learn
      </Link>
      <h1 className="font-display mt-2 text-3xl text-snow">{detail.title}</h1>
      <p className="mt-2 text-sm leading-relaxed text-mist">{detail.description}</p>
      <p className="mt-3 text-xs tracking-wide text-goldsoft">
        {done}/{detail.steps.length} studied
      </p>

      <ol className="mt-8 space-y-5">
        {detail.steps.map((step, i) => (
          <li
            key={step.key}
            className="overflow-hidden rounded-lg bg-paper text-paperink shadow-[0_1px_0_rgba(198,165,72,0.55),0_10px_28px_rgba(0,0,0,0.35)]"
          >
            <div className="h-px bg-gradient-to-r from-transparent via-gold to-transparent" />
            <div className="p-5 sm:p-6">
              <p className="text-xs tracking-wide text-paperfaint">
                Step {i + 1} · {step.kind === "quran" ? `Quran ${step.reference}` : step.reference}
                {step.grading ? ` · ${step.grading}` : ""}
              </p>
              <h2 className="font-display mt-1 text-lg">{step.title}</h2>
              {step.arabic && (
                <p lang="ar" className="mt-3 text-right text-xl leading-[2.2]">
                  {step.arabic}
                </p>
              )}
              {step.text && (
                <p className="mt-3 border-t border-paperline pt-3 font-serif leading-relaxed text-paperink/90">
                  {step.text}
                </p>
              )}
              <div className="mt-4 flex items-center justify-between">
                <Link
                  href={`/search?q=${encodeURIComponent(step.reference)}`}
                  className="text-xs text-paperfaint underline decoration-gold/50 underline-offset-4 hover:text-paperink"
                >
                  Open in search
                </Link>
                <button
                  type="button"
                  onClick={() => markStudied(step)}
                  disabled={step.completed}
                  className={
                    step.completed
                      ? "rounded-full border border-gold/40 px-4 py-1 text-xs font-bold text-[#8a6d1f]"
                      : "rounded-full bg-gold px-4 py-1 text-xs font-bold text-ink hover:opacity-90"
                  }
                >
                  {step.completed ? "✓ Studied" : "Mark studied"}
                </button>
              </div>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
