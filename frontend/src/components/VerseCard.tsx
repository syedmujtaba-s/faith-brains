import Link from "next/link";
import SaveButton from "@/components/SaveButton";
import TafsirToggle from "@/components/TafsirToggle";
import { arabicNumber } from "@/lib/api";

// The signature element: an illuminated verse panel — paper surface, gold hairline,
// Arabic set right-to-left in Amiri with a mushaf-style ayah medallion.
export default function VerseCard({
  surah,
  ayah,
  arabic,
  translation,
  surahName,
  linkToSurah = false,
}: {
  surah: number;
  ayah: number;
  arabic: string;
  translation: string | null;
  surahName?: string | null;
  linkToSurah?: boolean;
}) {
  const reference = `${surah}:${ayah}`;
  return (
    <article className="overflow-hidden rounded-lg bg-paper text-paperink shadow-[0_1px_0_rgba(198,165,72,0.55),0_10px_28px_rgba(0,0,0,0.35)]">
      <div className="h-px bg-gradient-to-r from-transparent via-gold to-transparent" />
      <div className="p-5 sm:p-6">
        <p lang="ar" className="text-right text-2xl leading-[2.3] sm:text-[1.7rem]">
          {arabic} <span className="medallion align-middle">{arabicNumber(ayah)}</span>
        </p>
        {translation && (
          <p className="mt-4 border-t border-paperline pt-4 font-serif text-[1.05rem] leading-relaxed text-paperink/90">
            {translation}
          </p>
        )}
        <div className="mt-4 flex items-center justify-between text-xs text-paperfaint">
          <span className="tracking-wide">
            {linkToSurah ? (
              <Link href={`/quran/${surah}`} className="underline decoration-gold/50 underline-offset-4 hover:text-paperink">
                {surahName ? `${surahName} · ` : ""}Quran {reference}
              </Link>
            ) : (
              <>{surahName ? `${surahName} · ` : ""}Quran {reference}</>
            )}
          </span>
          <SaveButton
            onPaper
            item={{
              id: `quran:${reference}`,
              kind: "quran",
              reference: `Quran ${reference}`,
              arabic,
              english: translation,
              href: `/quran/${surah}`,
            }}
          />
        </div>
        <TafsirToggle surah={surah} ayah={ayah} />
      </div>
    </article>
  );
}
