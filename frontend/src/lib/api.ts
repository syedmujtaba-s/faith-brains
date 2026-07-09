// Server components call FastAPI directly; client components go through the
// same-origin /api/v1 rewrite (see next.config.ts).
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8000";

export type Surah = {
  number: number;
  name_arabic: string;
  name_english: string;
  name_transliterated: string;
  revelation_place: string;
  revelation_order: number | null;
  ayah_count: number;
};

export type Translation = { edition: string; text: string; footnotes: string | null };

export type Verse = {
  surah: number;
  ayah: number;
  reference: string;
  text_uthmani: string;
  text_simple: string;
  basmala_prefix: string | null;
  juz: number | null;
  page: number | null;
  sajda: string | null;
  translations: Translation[];
};

export type SurahDetail = { surah: Surah; verses: Verse[] };

export type Grading = { name: string | null; grade: string | null };

export type Hadith = {
  collection: string;
  collection_name: string;
  number: string;
  book_number: string | null;
  book_name: string | null;
  number_in_book: string | null;
  text_arabic: string | null;
  text_english: string | null;
  gradings: Grading[];
  reference_schemes: Record<string, string | null>;
};

export type HadithList = {
  collection: string;
  collection_name: string;
  total: number;
  offset: number;
  limit: number;
  items: Hadith[];
};

export type Collection = {
  key: string;
  name_english: string;
  name_arabic: string | null;
  hadith_count: number;
};

export type SearchResult = {
  type: "quran" | "hadith";
  score: number;
  signals: string[];
  reference: string;
  surah?: number | null;
  ayah?: number | null;
  surah_name?: string | null;
  surah_name_arabic?: string | null;
  arabic?: string | null;
  translation?: string | null;
  collection?: string | null;
  collection_name?: string | null;
  number?: string | null;
  english?: string | null;
  gradings?: Grading[] | null;
};

export type SearchResponse = {
  query: string;
  scope: string;
  mode: string;
  signals_used: string[];
  results: SearchResult[];
};

export type AskResponse = {
  question: string;
  category: "educational" | "fatwa_seeking" | "sensitive_crisis" | "out_of_scope";
  answer: string;
  sources: SearchResult[];
  disclaimer: string;
};

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BACKEND}/api/v1${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API ${res.status} for ${path}`);
  return res.json();
}

export const api = {
  surahs: () => get<Surah[]>("/quran/surahs"),
  surah: (n: number) => get<SurahDetail>(`/quran/${n}`),
  collections: () => get<Collection[]>("/hadith/collections"),
  hadithList: (key: string, offset: number, limit = 20) =>
    get<HadithList>(`/hadith/${key}?offset=${offset}&limit=${limit}`),
  search: (q: string, scope = "all") =>
    get<SearchResponse>(`/search?q=${encodeURIComponent(q)}&scope=${scope}`),
};

const ARABIC_DIGITS = ["٠", "١", "٢", "٣", "٤", "٥", "٦", "٧", "٨", "٩"];

export function arabicNumber(n: number | string): string {
  return String(n)
    .split("")
    .map((c) => (/\d/.test(c) ? ARABIC_DIGITS[Number(c)] : c))
    .join("");
}

export function saheeh(verse: Verse): string | null {
  return verse.translations.find((t) => t.edition === "english_saheeh")?.text ?? null;
}
