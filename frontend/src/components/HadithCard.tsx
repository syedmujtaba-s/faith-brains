import SaveButton from "@/components/SaveButton";
import type { Grading } from "@/lib/api";

function gradeTone(grade: string | null): string {
  const g = (grade ?? "").toLowerCase();
  if (g.includes("sahih")) return "bg-[#2f5d43] text-[#d9efe0]";
  if (g.includes("hasan")) return "bg-[#4f5a2e] text-[#e9efd2]";
  if (g.includes("daif") || g.includes("da'if") || g.includes("weak"))
    return "bg-[#6b3d33] text-[#f4ddd6]";
  return "bg-raise text-mist";
}

export default function HadithCard({
  collection,
  collectionName,
  number,
  english,
  arabic,
  gradings,
  bookName,
}: {
  collection: string;
  collectionName: string;
  number: string;
  english: string | null;
  arabic: string | null;
  gradings: Grading[];
  bookName?: string | null;
}) {
  const shown = gradings.slice(0, 2);
  return (
    <article className="rounded-lg border border-line bg-lapis p-5">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm tracking-wide text-goldsoft">
          {collectionName} · {number}
          {bookName ? <span className="text-mist"> — {bookName}</span> : null}
        </p>
        <SaveButton
          item={{
            id: `hadith:${collection}:${number}`,
            kind: "hadith",
            reference: `${collectionName} ${number}`,
            arabic,
            english,
            href: `/hadith/${collection}`,
          }}
        />
      </div>
      {english && <p className="mt-3 font-serif leading-relaxed text-snow/90">{english}</p>}
      {arabic && (
        <p lang="ar" className="mt-4 border-t border-line pt-4 text-right text-xl leading-[2.1] text-snow/85">
          {arabic}
        </p>
      )}
      {shown.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {shown.map((g, i) => (
            <span key={i} className={`rounded-full px-2.5 py-0.5 text-xs ${gradeTone(g.grade)}`}>
              {g.grade}
              {g.name ? ` — ${g.name}` : ""}
            </span>
          ))}
        </div>
      )}
    </article>
  );
}
