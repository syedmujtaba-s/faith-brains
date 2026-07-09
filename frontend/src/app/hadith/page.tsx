import Link from "next/link";
import { api } from "@/lib/api";

export const metadata = { title: "Hadith — FaithBrains" };

export default async function HadithPage() {
  const collections = await api.collections();
  return (
    <div>
      <h1 className="font-display mb-2 text-3xl text-snow">Hadith collections</h1>
      <p className="mb-6 max-w-2xl text-sm text-mist">
        Ten classical collections with Arabic, English, and scholarly gradings where available.
      </p>
      <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {collections.map((c) => (
          <li key={c.key}>
            <Link
              href={`/hadith/${c.key}`}
              className="flex items-center justify-between gap-4 rounded-lg border border-line bg-lapis p-5 transition-colors hover:border-gold/50 hover:bg-raise"
            >
              <span>
                <span className="block text-snow">{c.name_english}</span>
                <span className="block text-xs text-mist">
                  {c.hadith_count.toLocaleString()} hadith
                </span>
              </span>
              {c.name_arabic && (
                <span lang="ar" className="text-xl text-goldsoft/90">
                  {c.name_arabic}
                </span>
              )}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
