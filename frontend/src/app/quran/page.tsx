import Link from "next/link";
import { api, arabicNumber } from "@/lib/api";

export const metadata = { title: "Quran — FaithBrains" };

export default async function QuranPage() {
  const surahs = await api.surahs();
  return (
    <div>
      <h1 className="font-display mb-6 text-3xl text-snow">The Quran</h1>
      <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {surahs.map((s) => (
          <li key={s.number}>
            <Link
              href={`/quran/${s.number}`}
              className="flex items-center gap-4 rounded-lg border border-line bg-lapis p-4 transition-colors hover:border-gold/50 hover:bg-raise"
            >
              <span className="medallion medallion-dark shrink-0">{arabicNumber(s.number)}</span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-snow">{s.name_transliterated}</span>
                <span className="block text-xs text-mist">
                  {s.name_english} · {s.ayah_count} ayat · {s.revelation_place}
                </span>
              </span>
              <span lang="ar" className="shrink-0 text-xl text-goldsoft/90">
                {s.name_arabic}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
