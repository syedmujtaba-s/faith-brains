import Link from "next/link";
import { notFound } from "next/navigation";
import VerseCard from "@/components/VerseCard";
import { api, saheeh } from "@/lib/api";

export default async function SurahPage({ params }: { params: Promise<{ surah: string }> }) {
  const { surah: raw } = await params;
  const n = Number(raw);
  if (!Number.isInteger(n) || n < 1 || n > 114) notFound();

  const detail = await api.surah(n).catch(() => null);
  if (!detail) notFound();
  const { surah, verses } = detail;
  const basmala = verses[0]?.basmala_prefix;

  return (
    <div className="mx-auto max-w-3xl">
      <header className="mb-8 text-center">
        <p lang="ar" className="text-4xl text-goldsoft">
          {surah.name_arabic}
        </p>
        <h1 className="font-display mt-2 text-2xl text-snow">
          {surah.number}. {surah.name_transliterated}
        </h1>
        <p className="mt-1 text-sm text-mist">
          {surah.name_english} · {surah.ayah_count} ayat · {surah.revelation_place}
        </p>
      </header>

      {basmala && (
        <p lang="ar" className="mb-8 text-center text-2xl text-snow/90">
          {basmala}
        </p>
      )}

      <div className="space-y-4">
        {verses.map((v) => (
          <VerseCard
            key={v.ayah}
            surah={v.surah}
            ayah={v.ayah}
            arabic={v.text_uthmani}
            translation={saheeh(v)}
          />
        ))}
      </div>

      <nav className="mt-10 flex justify-between text-sm">
        {n > 1 ? (
          <Link href={`/quran/${n - 1}`} className="text-goldsoft hover:underline">
            ← Surah {n - 1}
          </Link>
        ) : (
          <span />
        )}
        {n < 114 ? (
          <Link href={`/quran/${n + 1}`} className="text-goldsoft hover:underline">
            Surah {n + 1} →
          </Link>
        ) : (
          <span />
        )}
      </nav>
    </div>
  );
}
