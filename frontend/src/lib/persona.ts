// Self-chosen learning role (the four spec personas). Stored locally and
// mirrored to the anonymous learner record — it's a lens on the experience,
// not a profile: no account, no belief data.

import { sessionHeaders } from "@/lib/session";

export type PersonaKey = "learner" | "student" | "educator" | "new_muslim";

export const PERSONA_KEYS: readonly PersonaKey[] = [
  "learner",
  "student",
  "educator",
  "new_muslim",
];

const KEY = "faithbrains.persona.v1";
const ONBOARDED = "faithbrains.onboarded.v1";

export function loadPersona(): PersonaKey | null {
  if (typeof window === "undefined") return null;
  try {
    const v = window.localStorage.getItem(KEY);
    return PERSONA_KEYS.includes(v as PersonaKey) ? (v as PersonaKey) : null;
  } catch {
    return null;
  }
}

export function savePersona(p: PersonaKey | null): void {
  try {
    if (p) window.localStorage.setItem(KEY, p);
    else window.localStorage.removeItem(KEY);
  } catch {
    // storage blocked — the server mirror below still remembers the choice
  }
  fetch("/api/v1/learner/persona", {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...sessionHeaders() },
    body: JSON.stringify({ persona: p }),
  }).catch(() => {}); // offline is fine — localStorage drives the UI
}

export function isOnboarded(): boolean {
  if (typeof window === "undefined") return true; // never flash the overlay in SSR markup
  try {
    return window.localStorage.getItem(ONBOARDED) === "1";
  } catch {
    return true;
  }
}

export function setOnboarded(): void {
  try {
    window.localStorage.setItem(ONBOARDED, "1");
  } catch {
    // ignore — worst case the welcome shows again next visit
  }
}
