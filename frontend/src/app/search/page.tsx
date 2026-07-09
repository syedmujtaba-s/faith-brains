import HadithCard from "@/components/HadithCard";
import VerseCard from "@/components/VerseCard";
import { api } from "@/lib/api";

export const metadata = { title: "Search — FaithBrains" };

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; scope?: string }>;
}) {
  const { q, scope } = await searchParams;
  const query = (q ?? "").trim();
  const activeScope = scope === "quran" || scope === "hadith" ? scope : "all";
  const outcome = query ? await api.search(query, activeScope) : null;

  return (
    <div className="mx-auto max-w-3xl">
      <form action="/search" className="mb-6 flex gap-2">
        <input
          type="search"
          name="q"
          defaultValue={query}
          placeholder="Search — a topic, a phrase, 2:255, bukhari 6018, or Arabic"
          className="w-full rounded-full border border-line bg-lapis px-5 py-2.5 text-snow placeholder:text-mist/60"
        />
        <button type="submit" className="rounded-full bg-gold px-6 text-sm font-bold text-ink">
          Search
        </button>
      </form>

      {outcome && (
        <>
          <p className="mb-5 text-xs text-mist">
            {outcome.results.length} results · matched by{" "}
            {outcome.mode === "reference" ? "exact reference" : outcome.signals_used.join(" + ")}
          </p>
          {outcome.results.length === 0 && (
            <div className="rounded-lg border border-line bg-lapis p-6 text-center text-mist">
              Nothing matched. Try different words, an exact reference like{" "}
              <span className="text-goldsoft">2:255</span>, or Arabic.
            </div>
          )}
          <div className="space-y-4">
            {outcome.results.map((r, i) =>
              r.type === "quran" ? (
                <VerseCard
                  key={`q-${i}`}
                  surah={r.surah!}
                  ayah={r.ayah!}
                  arabic={r.arabic ?? ""}
                  translation={r.translation ?? null}
                  surahName={r.surah_name}
                  linkToSurah
                />
              ) : (
                <HadithCard
                  key={`h-${i}`}
                  collection={r.collection ?? ""}
                  collectionName={r.collection_name ?? r.reference}
                  number={r.number ?? ""}
                  english={r.english ?? null}
                  arabic={r.arabic ?? null}
                  gradings={r.gradings ?? []}
                />
              ),
            )}
          </div>
        </>
      )}

      {!query && (
        <p className="text-center text-sm text-mist">
          Search across 6,236 verses and 36,512 hadith — by meaning, phrase, reference, or Arabic
          text.
        </p>
      )}
    </div>
  );
}
