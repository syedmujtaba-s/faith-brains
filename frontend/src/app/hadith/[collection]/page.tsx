import Link from "next/link";
import { notFound } from "next/navigation";
import HadithCard from "@/components/HadithCard";
import { api } from "@/lib/api";

const PAGE_SIZE = 20;

export default async function CollectionPage({
  params,
  searchParams,
}: {
  params: Promise<{ collection: string }>;
  searchParams: Promise<{ page?: string }>;
}) {
  const { collection } = await params;
  const { page: rawPage } = await searchParams;
  const page = Math.max(1, Number(rawPage) || 1);

  const list = await api
    .hadithList(collection, (page - 1) * PAGE_SIZE, PAGE_SIZE)
    .catch(() => null);
  if (!list) notFound();

  const pages = Math.max(1, Math.ceil(list.total / PAGE_SIZE));

  return (
    <div className="mx-auto max-w-3xl">
      <header className="mb-6">
        <h1 className="font-display text-3xl text-snow">{list.collection_name}</h1>
        <p className="mt-1 text-sm text-mist">
          {list.total.toLocaleString()} hadith · page {page} of {pages.toLocaleString()}
        </p>
      </header>

      <div className="space-y-4">
        {list.items.map((h) => (
          <HadithCard
            key={h.number}
            collection={h.collection}
            collectionName={h.collection_name}
            number={h.number}
            english={h.text_english}
            arabic={h.text_arabic}
            gradings={h.gradings}
            bookName={h.book_name}
          />
        ))}
      </div>

      <nav className="mt-8 flex items-center justify-between text-sm">
        {page > 1 ? (
          <Link href={`/hadith/${collection}?page=${page - 1}`} className="text-goldsoft hover:underline">
            ← Previous
          </Link>
        ) : (
          <span />
        )}
        {page < pages ? (
          <Link href={`/hadith/${collection}?page=${page + 1}`} className="text-goldsoft hover:underline">
            Next →
          </Link>
        ) : (
          <span />
        )}
      </nav>
    </div>
  );
}
