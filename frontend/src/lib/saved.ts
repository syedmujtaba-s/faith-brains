// Bookmarks live in localStorage until accounts exist (Milestone 4+).

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

export function toggleSaved(item: Omit<SavedItem, "savedAt">): boolean {
  const items = loadSaved();
  const exists = items.some((s) => s.id === item.id);
  const next = exists
    ? items.filter((s) => s.id !== item.id)
    : [{ ...item, savedAt: Date.now() }, ...items];
  window.localStorage.setItem(KEY, JSON.stringify(next));
  return !exists;
}

export function removeSaved(id: string): SavedItem[] {
  const next = loadSaved().filter((s) => s.id !== id);
  window.localStorage.setItem(KEY, JSON.stringify(next));
  return next;
}
