"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type {
  AskResponse,
  AskStreamEvent,
  ChatMessage,
  ConversationDetail,
  ConversationSummary,
  Persona,
  SearchResult,
} from "@/lib/api";
import {
  isOnboarded,
  loadPersona,
  savePersona,
  setOnboarded,
  type PersonaKey,
} from "@/lib/persona";
import { sessionHeaders } from "@/lib/session";
import PersonaOnboarding from "@/components/PersonaOnboarding";

// Fallback suggestions when no persona is chosen or the catalogue is unreachable
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

type PathSummary = {
  key: string;
  title: string;
  description: string;
  step_count: number;
  completed_count: number;
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
              <span
                key={i}
                className="mx-0.5 rounded bg-gold/15 px-1 align-super text-[0.7em] font-bold text-[#8a6d1f]"
              >
                {m[1]}
              </span>
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
    <div className="rounded-lg border border-line bg-lapis p-4">
      <p className="text-xs tracking-wide text-goldsoft">
        [{n}]{" "}
        {isQuran
          ? `Quran ${s.reference}${s.surah_name ? ` — ${s.surah_name}` : ""}`
          : s.reference}
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

function AssistantMessage({ msg }: { msg: ChatMessage }) {
  const sources = msg.sources ?? [];
  return (
    <div className="space-y-3">
      <div className="overflow-hidden rounded-lg bg-paper text-paperink shadow-[0_1px_0_rgba(198,165,72,0.55),0_10px_28px_rgba(0,0,0,0.35)]">
        <div className="h-px bg-gradient-to-r from-transparent via-gold to-transparent" />
        <div className="p-5 sm:p-6">
          {msg.category && (
            <p className="mb-4 inline-block rounded-full border border-gold/40 px-3 py-0.5 text-xs tracking-wide text-[#8a6d1f]">
              {CATEGORY_LABEL[msg.category]}
            </p>
          )}
          <AnswerBody text={msg.content || "…"} />
          {msg.disclaimer && (
            <p className="mt-6 border-t border-paperline pt-3 text-xs text-paperfaint">
              {msg.disclaimer}
            </p>
          )}
        </div>
      </div>
      {sources.length > 0 && (
        <details className="group">
          <summary className="cursor-pointer list-none text-xs tracking-wide text-goldsoft hover:text-gold">
            <span className="group-open:hidden">Show sources ({sources.length})</span>
            <span className="hidden group-open:inline">Hide sources</span>
          </summary>
          <div className="mt-3 space-y-3">
            {sources.map((s, i) => (
              <SourceCard key={i} n={i + 1} s={s} />
            ))}
          </div>
        </details>
      )}
    </div>
  );
}

export default function HomePage() {
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<number | null>(null);

  const [persona, setPersona] = useState<PersonaKey | null>(null);
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [recent, setRecent] = useState<ConversationSummary[]>([]);
  const [continuePath, setContinuePath] = useState<PathSummary | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const stored = loadPersona();
    setPersona(stored);
    if (!stored && !isOnboarded()) setShowOnboarding(true);

    fetch("/api/v1/personas")
      .then((r) => (r.ok ? r.json() : []))
      .then(setPersonas)
      .catch(() => {});
    refreshRecent();
    fetch("/api/v1/learn/paths", { headers: sessionHeaders() })
      .then((r) => (r.ok ? r.json() : []))
      .then((paths: PathSummary[]) => {
        const inProgress = paths
          .filter((p) => p.completed_count > 0 && p.completed_count < p.step_count)
          .sort((a, b) => b.completed_count / b.step_count - a.completed_count / a.step_count);
        setContinuePath(inProgress[0] ?? null);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (messages.length > 0) bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, busy]);

  function refreshRecent() {
    fetch("/api/v1/conversations", { headers: sessionHeaders() })
      .then((r) => (r.ok ? r.json() : []))
      .then((list: ConversationSummary[]) => setRecent(list.slice(0, 5)))
      .catch(() => {});
  }

  function choosePersona(p: PersonaKey | null) {
    setPersona(p);
    savePersona(p);
  }

  function newConversation() {
    setMessages([]);
    setConversationId(null);
    setError(null);
    refreshRecent();
  }

  async function loadConversation(id: number) {
    try {
      const res = await fetch(`/api/v1/conversations/${id}`, { headers: sessionHeaders() });
      if (!res.ok) return;
      const detail: ConversationDetail = await res.json();
      setMessages(
        detail.messages.map((m) => ({
          role: m.role === "assistant" ? "assistant" : "user",
          content: m.content,
          category: (m.category as AskResponse["category"]) ?? null,
          sources: m.sources ?? [],
        }))
      );
      setConversationId(id);
      setError(null);
    } catch {
      setError("Couldn't load that conversation. Try again.");
    }
  }

  async function submit(q: string) {
    const trimmed = q.trim();
    if (trimmed.length < 3 || busy) return;
    setBusy(true);
    setError(null);
    setQuestion("");
    const base: ChatMessage[] = [...messages, { role: "user", content: trimmed }];
    let assistant: ChatMessage = { role: "assistant", content: "", sources: [] };
    setMessages([...base, assistant]);

    const paint = () => setMessages([...base, { ...assistant }]);
    try {
      const res = await fetch("/api/v1/ask/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...sessionHeaders() },
        body: JSON.stringify({
          question: trimmed,
          ...(persona ? { persona } : {}),
          ...(conversationId ? { conversation_id: conversationId } : {}),
        }),
      });
      if (!res.ok || !res.body) {
        const body = await res.json().catch(() => null);
        setError(body?.detail ?? `Something went wrong (${res.status}). Try again.`);
        setMessages(base);
        return;
      }

      const apply = (evt: AskStreamEvent) => {
        if (evt.event === "meta" && evt.category) {
          assistant = { ...assistant, category: evt.category };
        } else if (evt.event === "sources" && evt.sources) {
          assistant = { ...assistant, sources: evt.sources };
        } else if (evt.event === "delta" && evt.text) {
          assistant = { ...assistant, content: assistant.content + evt.text };
        } else if (evt.event === "done") {
          assistant = {
            ...assistant,
            content: evt.answer ?? assistant.content,
            category: evt.category ?? assistant.category,
            sources: evt.sources ?? assistant.sources,
            disclaimer: evt.disclaimer ?? "",
          };
          if (evt.conversation_id) setConversationId(evt.conversation_id);
          refreshRecent();
        } else if (evt.event === "error") {
          setError(evt.detail ?? "The answer engine failed mid-response. Try again.");
          return;
        }
        paint();
      };

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        let sep;
        while ((sep = buf.indexOf("\n\n")) !== -1) {
          const frame = buf.slice(0, sep);
          buf = buf.slice(sep + 2);
          const data = frame.split("\n").find((l) => l.startsWith("data: "));
          if (data) apply(JSON.parse(data.slice(6)) as AskStreamEvent);
        }
      }
    } catch {
      setError("Could not reach the server. Try again in a moment.");
      setMessages(base);
    } finally {
      setBusy(false);
    }
  }

  const activePersona = personas.find((p) => p.key === persona) ?? null;
  const suggestions = activePersona?.suggested_questions ?? SAMPLES;
  const threadActive = messages.length > 0;

  return (
    <div className="mx-auto max-w-3xl">
      {showOnboarding && (
        <PersonaOnboarding
          personas={personas}
          onDone={(p) => {
            if (p) choosePersona(p);
            setOnboarded();
            setShowOnboarding(false);
          }}
        />
      )}

      {!threadActive && (
        <>
          <section className="pt-6 pb-8 text-center">
            <p lang="ar" className="text-3xl text-goldsoft/90">
              بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ
            </p>
            <h1 className="font-display mt-5 text-4xl text-snow sm:text-5xl">
              Ask, with sources.
            </h1>
            <p className="mx-auto mt-3 max-w-xl text-mist">
              FaithBrains is your companion for learning Islam — ask anything, follow up
              freely, and every answer is built only from the Quran and authentic hadith,
              each claim cited.
            </p>
          </section>

          <div className="mb-6">
            <p className="mb-2 text-center text-xs tracking-wide text-mist/70">
              I&apos;m learning as…
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              {(personas.length ? personas : []).map((p) => {
                const active = p.key === persona;
                return (
                  <button
                    key={p.key}
                    type="button"
                    title={p.tagline}
                    onClick={() => choosePersona(active ? null : (p.key as PersonaKey))}
                    className={
                      active
                        ? "rounded-full border border-gold/60 bg-raise px-3.5 py-1.5 text-xs text-goldsoft"
                        : "rounded-full border border-line px-3.5 py-1.5 text-xs text-mist hover:border-gold/60 hover:text-goldsoft"
                    }
                  >
                    {p.label}
                  </button>
                );
              })}
            </div>
          </div>

          {continuePath && (
            <Link
              href={`/learn/${continuePath.key}`}
              className="mb-6 block rounded-lg border border-line bg-lapis p-4 transition-colors hover:border-gold/50 hover:bg-raise"
            >
              <p className="text-xs tracking-wide text-goldsoft">Continue learning</p>
              <div className="mt-1 flex items-center justify-between gap-4">
                <span className="font-display text-snow">{continuePath.title}</span>
                <span className="shrink-0 text-xs text-mist">
                  {continuePath.completed_count}/{continuePath.step_count} studied
                </span>
              </div>
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-ink">
                <div
                  className="h-full rounded-full bg-gold"
                  style={{
                    width: `${Math.round((continuePath.completed_count / continuePath.step_count) * 100)}%`,
                  }}
                />
              </div>
            </Link>
          )}
        </>
      )}

      {threadActive && (
        <div className="flex items-center justify-between pt-4 pb-4">
          <span className="text-xs text-mist/80">
            {activePersona ? `Learning as ${activePersona.label}` : "FaithBrains"}
          </span>
          <button
            type="button"
            onClick={newConversation}
            className="rounded-full border border-line px-3.5 py-1.5 text-xs text-mist hover:border-gold/60 hover:text-goldsoft"
          >
            New conversation
          </button>
        </div>
      )}

      {threadActive && (
        <section className="space-y-5 pb-6">
          {messages.map((m, i) =>
            m.role === "user" ? (
              <div key={i} className="flex justify-end">
                <p className="max-w-[85%] rounded-2xl rounded-br-sm border border-line bg-raise px-4 py-2.5 text-sm text-snow">
                  {m.content}
                </p>
              </div>
            ) : (
              <AssistantMessage key={i} msg={m} />
            )
          )}
          <div ref={bottomRef} />
        </section>
      )}

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
          rows={threadActive ? 2 : 3}
          placeholder={
            threadActive
              ? "Ask a follow-up…"
              : "e.g. What does the Quran teach about patience in hardship?"
          }
          className="w-full resize-none bg-transparent px-2 py-1.5 text-snow placeholder:text-mist/60 focus:outline-none"
        />
        <div className="flex items-center justify-between px-2 pb-1">
          <span className="text-xs text-mist/70">Educational answers — never rulings.</span>
          <button
            type="submit"
            disabled={busy || question.trim().length < 3}
            className="rounded-full bg-gold px-5 py-1.5 text-sm font-bold text-ink transition-opacity disabled:opacity-40"
          >
            {busy ? "Consulting sources…" : threadActive ? "Send" : "Ask"}
          </button>
        </div>
      </form>

      {error && (
        <div className="mt-4 rounded-lg border border-[#6b3d33] bg-[#3a2320] p-4 text-sm text-[#f4ddd6]">
          {error}
        </div>
      )}

      {!threadActive && (
        <div className="mt-5 flex flex-wrap justify-center gap-2">
          {suggestions.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => submit(s)}
              className="rounded-full border border-line px-3.5 py-1.5 text-xs text-mist hover:border-gold/60 hover:text-goldsoft"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {!threadActive && recent.length > 0 && (
        <section className="mt-10">
          <h2 className="font-display mb-3 text-lg text-goldsoft">Recent conversations</h2>
          <div className="space-y-2">
            {recent.map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => loadConversation(c.id)}
                className="block w-full rounded-lg border border-line bg-lapis px-4 py-3 text-left transition-colors hover:border-gold/50 hover:bg-raise"
              >
                <span className="block truncate text-sm text-snow">{c.title}</span>
                <span className="mt-0.5 block text-xs text-mist/70">
                  {Math.floor(c.message_count / 2)}{" "}
                  {c.message_count >= 4 ? "exchanges" : "exchange"}
                </span>
              </button>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
