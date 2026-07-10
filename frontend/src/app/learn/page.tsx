import Link from "next/link";
import PathList from "@/components/PathList";

export const metadata = { title: "Learn — FaithBrains" };

const TOPICS: { title: string; arabic: string; query: string }[] = [
  { title: "Patience", arabic: "الصبر", query: "patience in hardship" },
  { title: "Gratitude", arabic: "الشكر", query: "gratitude and thankfulness" },
  { title: "Mercy", arabic: "الرحمة", query: "mercy of Allah" },
  { title: "Prayer", arabic: "الصلاة", query: "prayer and its reward" },
  { title: "Charity", arabic: "الصدقة", query: "charity and spending on the poor" },
  { title: "Forgiveness", arabic: "المغفرة", query: "forgiveness and repentance" },
  { title: "Justice", arabic: "العدل", query: "justice and fairness" },
  { title: "Knowledge", arabic: "العلم", query: "seeking knowledge" },
  { title: "Family", arabic: "الأسرة", query: "kindness to parents and family" },
  { title: "Honesty", arabic: "الصدق", query: "truthfulness and honesty" },
  { title: "Trust in God", arabic: "التوكل", query: "trust and reliance upon Allah" },
  { title: "The Hereafter", arabic: "الآخرة", query: "the hereafter and the day of judgment" },
];

export default function LearnPage() {
  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="font-display mb-2 text-3xl text-snow">Learning paths</h1>
      <p className="mb-6 text-sm text-mist">
        Guided journeys through the sources, one step at a time. Your progress is remembered.
      </p>
      <PathList />

      <h2 className="font-display mt-12 mb-2 text-2xl text-snow">Learn by theme</h2>
      <p className="mb-6 text-sm text-mist">
        Or start from a theme and read what the Quran and hadith actually say about it.
      </p>

      <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {TOPICS.map((t) => (
          <li key={t.title}>
            <Link
              href={`/search?q=${encodeURIComponent(t.query)}`}
              className="block rounded-lg border border-line bg-lapis p-4 text-center transition-colors hover:border-gold/50 hover:bg-raise"
            >
              <span lang="ar" className="block text-2xl text-goldsoft">
                {t.arabic}
              </span>
              <span className="mt-1 block text-sm text-snow">{t.title}</span>
            </Link>
          </li>
        ))}
      </ul>

      <section className="mt-12 rounded-lg border border-line bg-lapis p-6 text-sm leading-relaxed text-mist">
        <h2 className="font-display mb-3 text-lg text-goldsoft">About FaithBrains</h2>
        <p>
          FaithBrains is an educational companion for the Quran and Hadith. Answers on the Ask tab
          are generated strictly from retrieved sources, with every citation shown. It is not a
          religious authority: it does not issue fatwas or rulings, and where scholars differ it
          presents the difference rather than choosing a side. For personal guidance, please
          consult a qualified scholar.
        </p>
        <h3 className="mt-5 mb-2 text-snow">Sources &amp; attribution</h3>
        <ul className="list-disc space-y-1 pl-5">
          <li>
            Quran Arabic text from the{" "}
            <a href="https://tanzil.net" className="text-goldsoft underline underline-offset-2">
              Tanzil Project
            </a>{" "}
            (verbatim, unmodified).
          </li>
          <li>
            English translations — Saheeh International and Rowwad Translation Center — via{" "}
            <a href="https://quranenc.com" className="text-goldsoft underline underline-offset-2">
              QuranEnc.com
            </a>
            , reproduced verbatim with edition versions preserved.
          </li>
          <li>Hadith corpus from the open fawazahmed0/hadith-api dataset.</li>
        </ul>
      </section>
    </div>
  );
}
