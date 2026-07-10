"use client";

import type { Persona } from "@/lib/api";
import type { PersonaKey } from "@/lib/persona";

// Rendered if the API list hasn't arrived (or fails) so the welcome never breaks.
const FALLBACK: Persona[] = [
  {
    key: "learner",
    label: "Learner",
    tagline: "Plain-language answers to your questions, with every source cited.",
    suggested_questions: [],
    recommended_paths: [],
  },
  {
    key: "student",
    label: "Student of knowledge",
    tagline: "Precise, source-linked study with references and gradings.",
    suggested_questions: [],
    recommended_paths: [],
  },
  {
    key: "educator",
    label: "Educator / Imam",
    tagline: "Structured, citable material ready for classes and khutbahs.",
    suggested_questions: [],
    recommended_paths: [],
  },
  {
    key: "new_muslim",
    label: "New Muslim",
    tagline: "A gentle, accurate introduction — one step at a time.",
    suggested_questions: [],
    recommended_paths: [],
  },
];

export default function PersonaOnboarding({
  personas,
  onDone,
}: {
  personas: Persona[];
  onDone: (persona: PersonaKey | null) => void;
}) {
  const list = personas.length === 4 ? personas : FALLBACK;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/85 p-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-xl border border-line bg-lapis p-6 shadow-[0_20px_60px_rgba(0,0,0,0.5)] sm:p-8">
        <div className="text-center">
          <p lang="ar" className="text-2xl text-goldsoft/90">
            السَّلَامُ عَلَيْكُمْ
          </p>
          <h2 className="font-display mt-3 text-2xl text-snow">Welcome to FaithBrains</h2>
          <p className="mx-auto mt-2 max-w-sm text-sm text-mist">
            A study companion grounded in the Quran and authentic hadith — every answer
            cited. Choose how you&apos;d like to learn:
          </p>
        </div>
        <div className="mt-6 grid gap-3 sm:grid-cols-2">
          {list.map((p) => (
            <button
              key={p.key}
              type="button"
              onClick={() => onDone(p.key as PersonaKey)}
              className="rounded-lg border border-line bg-ink/40 p-4 text-left transition-colors hover:border-gold/60 hover:bg-raise"
            >
              <span className="font-display block text-base text-snow">{p.label}</span>
              <span className="mt-1 block text-xs leading-relaxed text-mist">{p.tagline}</span>
            </button>
          ))}
        </div>
        <div className="mt-5 text-center">
          <button
            type="button"
            onClick={() => onDone(null)}
            className="text-xs text-mist/80 underline decoration-line underline-offset-4 hover:text-goldsoft"
          >
            Skip for now — you can choose any time
          </button>
        </div>
      </div>
    </div>
  );
}
