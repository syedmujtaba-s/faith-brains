"""Import the hadith corpus from the fawazahmed0/hadith-api dataset (local raw files).

English rows drive the import; Arabic rows are merged by hadith number. Gradings and
in-book references are preserved as JSON. See docs/licensing.md for the copyright
caveat on the English translations (public-launch blocker, fine for dev/beta).

Run:  uv run python -m app.ingest.hadith_fawazahmed
"""

import asyncio
import json

from sqlalchemy import delete, select

from app.db.engine import get_sessionmaker
from app.db.models import HadithCollection, HadithRecord
from app.ingest.common import RAW, upsert_edition
from app.retrieval.arabic import normalize_arabic

COLLECTIONS = {
    "bukhari": ("Sahih al-Bukhari", "صحيح البخاري"),
    "muslim": ("Sahih Muslim", "صحيح مسلم"),
    "abudawud": ("Sunan Abi Dawud", "سنن أبي داود"),
    "tirmidhi": ("Jami` at-Tirmidhi", "جامع الترمذي"),
    "nasai": ("Sunan an-Nasa'i", "سنن النسائي"),
    "ibnmajah": ("Sunan Ibn Majah", "سنن ابن ماجه"),
    "malik": ("Muwatta Malik", "موطأ مالك"),
    "nawawi": ("An-Nawawi's Forty Hadith", "الأربعون النووية"),
    "qudsi": ("Forty Hadith Qudsi", "الأحاديث القدسية"),
    "dehlawi": ("Forty Hadith of Shah Waliullah Dehlawi", "أربعون الدهلوي"),
}


def num_str(value) -> str:
    """hadithnumber can be int or float (sub-numbered variants) — canonical string form."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip().lower()


def load(key: str, lang: str) -> dict | None:
    path = RAW / "hadith" / f"{key}-{lang}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


async def import_collection(session, key: str) -> int:
    eng = load(key, "eng")
    ara = load(key, "ara")
    if eng is None:
        print(f"  {key}: no English file, skipping")
        return 0

    sections = {str(k): (v or "").strip() for k, v in eng.get("metadata", {}).get("sections", {}).items()}
    ara_by_number = {}
    if ara:
        for h in ara.get("hadiths", []):
            ara_by_number[num_str(h.get("hadithnumber"))] = h.get("text")

    collection = (
        await session.execute(select(HadithCollection).where(HadithCollection.key == key))
    ).scalar_one_or_none()
    if collection is None:
        collection = HadithCollection(key=key)
        session.add(collection)
    collection.name_english = COLLECTIONS[key][0]
    collection.name_arabic = COLLECTIONS[key][1]
    await session.flush()

    await session.execute(delete(HadithRecord).where(HadithRecord.collection_id == collection.id))

    records = []
    seen: set[str] = set()
    for h in eng.get("hadiths", []):
        number = num_str(h.get("hadithnumber"))
        if number in seen:
            continue
        seen.add(number)
        ref = h.get("reference") or {}
        book = ref.get("book")
        text_arabic = ara_by_number.get(number)
        gradings = [
            {"name": g.get("name"), "grade": g.get("grade")}
            for g in (h.get("grades") or [])
            if g.get("grade")
        ]
        records.append(
            HadithRecord(
                collection_id=collection.id,
                hadith_number=number,
                arabic_number=num_str(h.get("arabicnumber")) if h.get("arabicnumber") is not None else None,
                book_number=str(book) if book is not None else None,
                book_name=sections.get(str(book)) or None,
                number_in_book=str(ref["hadith"]) if ref.get("hadith") is not None else None,
                text_arabic=text_arabic,
                text_arabic_normalized=normalize_arabic(text_arabic) if text_arabic else None,
                text_english=(h.get("text") or "").strip() or None,
                gradings=gradings,
                reference_schemes={
                    "in_book": (
                        f"Book {book}, Hadith {ref.get('hadith')}" if book is not None else None
                    ),
                },
            )
        )
    collection.canonical_count = len(records)
    session.add_all(records)
    print(f"  {key}: {len(records)} hadiths (arabic matched: {sum(1 for r in records if r.text_arabic)})")
    return len(records)


async def run() -> None:
    async with get_sessionmaker()() as session:
        total = 0
        for key in COLLECTIONS:
            total += await import_collection(session, key)
        await upsert_edition(
            session,
            key="hadith_fawazahmed",
            kind="hadith",
            name="fawazahmed0/hadith-api open dataset",
            language="ar+en",
            source_url="https://github.com/fawazahmed0/hadith-api",
            license_name="Unlicense (dataset); underlying English translations unresolved — see docs/licensing.md",
            attribution="Hadith data from the fawazahmed0/hadith-api open dataset",
            version="1",
        )
        await session.commit()
        print(f"total hadiths imported: {total}")


if __name__ == "__main__":
    asyncio.run(run())
