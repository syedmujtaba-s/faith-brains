// Bookmarks render from localStorage (holds display text) and mirror to the
// server keyed by the anonymous session (lib/session.ts), so they survive
// cache clears and can be claimed by future accounts.

import { sessionHeaders } from "@/lib/session";

export type SavedItem = {
  id: string; // e.g. "quran:2:255" | "hadith:bukhari:6018"
  kind: "quran" | "hadith";
  reference: string;
  arabic: string | null;
  english: string | null;
  href: string;
  savedAt: number;
};

const KEY = "faithbrains.saved.v1";

export function loadSaved(): SavedItem[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(window.localStorage.getItem(KEY) ?? "[]");
  } catch {
    return [];
  }
}

export function isSaved(id: string): boolean {
  return loadSaved().some((s) => s.id === id);
}

function serverRef(item: Pick<SavedItem, "id" | "kind">): string {
  // "quran:2:255" -> "2:255"; "hadith:bukhari:6018" -> "bukhari 6018"
  const rest = item.id.slice(item.kind.length + 1);
  return item.kind === "hadith" ? rest.replace(":", " ") : rest;
}

function syncServer(item: Pick<SavedItem, "id" | "kind">, saved: boolean): void {
  const reference = serverRef(item);
  const headers = { "Content-Type": "application/json", ...sessionHeaders() };
  const req = saved
    ? fetch("/api/v1/saved", {
        method: "POST",
        headers,
        body: JSON.stringify({ kind: item.kind, reference }),
      })
    : fetch(
        `/api/v1/saved?kind=${item.kind}&reference=${encodeURIComponent(reference)}`,
        { method: "DELETE", headers }
      );
  req.catch(() => {}); // offline is fine — localStorage remains the display source
}

export function toggleSaved(item: Omit<SavedItem, "savedAt">): boolean {
  const items = loadSaved();
  const exists = items.some((s) => s.id === item.id);
  const next = exists
    ? items.filter((s) => s.id !== item.id)
    : [{ ...item, savedAt: Date.now() }, ...items];
  window.localStorage.setItem(KEY, JSON.stringify(next));
  syncServer(item, !exists);
  return !exists;
}

export function removeSaved(id: string): SavedItem[] {
  const items = loadSaved();
  const removed = items.find((s) => s.id === id);
  const next = items.filter((s) => s.id !== id);
  window.localStorage.setItem(KEY, JSON.stringify(next));
  if (removed) syncServer(removed, false);
  return next;
}
