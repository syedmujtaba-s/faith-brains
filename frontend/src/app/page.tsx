"use client";

import { useState } from "react";
import type { AskResponse, SearchResult } from "@/lib/api";

const SAMPLES = [
  "What does the Quran say about patience?",
  "How should I treat my parents?",
  "What is the reward for charity?",
  "Which hadith is about intentions?",
];

const CATEGORY_LABEL: Record<AskResponse["category"], string> = {
  educational: "Educational answer",
  fatwa_seeking: "General teaching — not a ruling",
  sensitive_crisis: "Please seek support",
  out_of_scope: "Outside FaithBrains' scope",
};

function AnswerBody({ text }: { text: string }) {
  return (
    <div className="space-y-4">
      {text.split(/\n{2,}/).map((para, pi) => (
        <p key={pi} className="font-serif leading-relaxed text-paperink/95">
          {para.split(/(\[\d+\])/g).map((part, i) => {
            const m = /^\[(\d+)\]$/.exec(part);
            if (!m) return <span key={i}>{part}</span>;
            return (
              <a
                key={i}
                href={`#src-${m[1]}`}
                className="mx-0.5 rounded bg-gold/15 px-1 align-super text-[0.7em] font-bold text-[#8a6d1f]"
              >
                {m[1]}
              </a>
            );
          })}
        </p>
      ))}
    </div>
  );
}

function SourceCard({ n, s }: { n: number; s: SearchResult }) {
  const isQuran = s.type === "quran";
  return (
    <div id={`src-${n}`} className="rounded-lg border border-line bg-lapis p-4 scroll-mt-24">
      <p className="text-xs tracking-wide text-goldsoft">
        [{n}] {isQuran ? `Quran ${s.reference}${s.surah_name ? ` — ${s.surah_name}` : ""}` : s.reference}
      </p>
      <p className="mt-2 text-sm font-serif leading-relaxed text-snow/90">
        {isQuran ? s.translation : s.english}
      </p>
      {s.arabic && (
        <p lang="ar" className="mt-2 text-right text-lg leading-[2] text-snow/80">
          {s.arabic}
        </p>
      )}
    </div>
  );
}

export default function AskPage() {
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AskResponse | null>(null);

  async function submit(q: string) {
    const trimmed = q.trim();
    if (trimmed.length < 3 || busy) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch("/api/v1/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: trimmed }),
      });
      const body = await res.json();
      if (!res.ok) {
        setError(body.detail ?? `Something went wrong (${res.status}). Try again.`);
      } else {
        setResult(body);
      }
    } catch {
      setError("Could not reach the server. Is the backend running?");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <section className="pt-6 pb-10 text-center">
        <p lang="ar" className="text-3xl text-goldsoft/90">
          بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ
        </p>
        <h1 className="font-display mt-5 text-4xl text-snow sm:text-5xl">Ask, with sources.</h1>
        <p className="mx-auto mt-3 max-w-xl text-mist">
          Every answer is built only from the Quran and authentic hadith retrieved for your
          question — each claim cited, every source shown.
        </p>
      </section>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit(question);
        }}
        className="rounded-xl border border-line bg-lapis p-3"
      >
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit(question);
            }
          }}
          rows={3}
          placeholder="e.g. What does the Quran teach about patience in hardship?"
          className="w-full resize-none bg-transparent px-2 py-1.5 text-snow placeholder:text-mist/60 focus:outline-none"
        />
        <div className="flex items-center justify-between px-2 pb-1">
          <span className="text-xs text-mist/70">Educational answers — never rulings.</span>
          <button
            type="submit"
            disabled={busy || question.trim().length < 3}
            className="rounded-full bg-gold px-5 py-1.5 text-sm font-bold text-ink transition-opacity disabled:opacity-40"
          >
            {busy ? "Consulting sources…" : "Ask"}
          </button>
        </div>
      </form>

      {!result && !busy && (
        <div className="mt-5 flex flex-wrap justify-center gap-2">
          {SAMPLES.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => {
                setQuestion(s);
                submit(s);
              }}
              className="rounded-full border border-line px-3.5 py-1.5 text-xs text-mist hover:border-gold/60 hover:text-goldsoft"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {error && (
        <div className="mt-6 rounded-lg border border-[#6b3d33] bg-[#3a2320] p-4 text-sm text-[#f4ddd6]">
          {error}
        </div>
      )}

      {result && (
        <section className="mt-8 space-y-6">
          <div className="overflow-hidden rounded-lg bg-paper text-paperink shadow-[0_1px_0_rgba(198,165,72,0.55),0_10px_28px_rgba(0,0,0,0.35)]">
            <div className="h-px bg-gradient-to-r from-transparent via-gold to-transparent" />
            <div className="p-6">
              <p className="mb-4 inline-block rounded-full border border-gold/40 px-3 py-0.5 text-xs tracking-wide text-[#8a6d1f]">
                {CATEGORY_LABEL[result.category]}
              </p>
              <AnswerBody text={result.answer} />
              <p className="mt-6 border-t border-paperline pt-3 text-xs text-paperfaint">
                {result.disclaimer}
              </p>
            </div>
          </div>

          {result.sources.length > 0 && (
            <div>
              <h2 className="font-display mb-3 text-lg text-goldsoft">Sources</h2>
              <div className="space-y-3">
                {result.sources.map((s, i) => (
                  <SourceCard key={i} n={i + 1} s={s} />
                ))}
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
