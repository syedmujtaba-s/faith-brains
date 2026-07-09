"""Enrich surahs and verses with Tanzil quran-data.xml metadata.

Fills surah names (English/transliterated), revelation place/order, and per-verse
juz / hizb quarter / ruku / manzil / page / sajda by walking boundary markers.

Run after quran_tanzil:  uv run python -m app.ingest.quran_metadata
"""

import asyncio
import xml.etree.ElementTree as ET

from sqlalchemy import select

from app.db.engine import get_sessionmaker
from app.db.models import QuranVerse, Surah
from app.ingest.common import RAW

DATA_XML = RAW / "tanzil" / "quran-data.xml"


def boundaries(root, container: str, element: str) -> list[tuple[int, int, int]]:
    """[(sura, aya, index)] sorted — start markers for juz/hizb/ruku/manzil/page."""
    out = []
    parent = root.find(container)
    if parent is None:
        return out
    for el in parent.iter(element):
        out.append((int(el.get("sura")), int(el.get("aya")), int(el.get("index"))))
    out.sort()
    return out


def assign(verse_keys: list[tuple[int, int]], marks: list[tuple[int, int, int]]) -> dict:
    """Map each (sura, aya) to the index of the last boundary at or before it."""
    result = {}
    pos = -1
    current = None
    for key in verse_keys:  # verse_keys must be globally sorted
        while pos + 1 < len(marks) and (marks[pos + 1][0], marks[pos + 1][1]) <= key:
            pos += 1
            current = marks[pos][2]
        result[key] = current
    return result


async def run() -> None:
    if not DATA_XML.exists():
        raise SystemExit(f"missing {DATA_XML} — run scripts/download_sources.py first")
    root = ET.parse(DATA_XML).getroot()

    async with get_sessionmaker()() as session:
        surahs = {s.number: s for s in (await session.execute(select(Surah))).scalars().all()}
        if len(surahs) != 114:
            raise SystemExit("surahs table not populated — run quran_tanzil first")

        for el in root.find("suras").iter("sura"):
            s = surahs[int(el.get("index"))]
            s.name_transliterated = el.get("tname")
            s.name_english = el.get("ename")
            s.revelation_place = el.get("type")
            s.revelation_order = int(el.get("order"))
            expected = int(el.get("ayas"))
            if s.ayah_count != expected:
                raise SystemExit(
                    f"surah {s.number}: imported {s.ayah_count} ayahs, metadata says {expected}"
                )

        verses = (
            (await session.execute(select(QuranVerse).order_by(QuranVerse.surah_number, QuranVerse.ayah_number)))
            .scalars()
            .all()
        )
        keys = [(v.surah_number, v.ayah_number) for v in verses]

        juz = assign(keys, boundaries(root, "juzs", "juz"))
        hizb = assign(keys, boundaries(root, "hizbs", "quarter"))
        ruku = assign(keys, boundaries(root, "rukus", "ruku"))
        manzil = assign(keys, boundaries(root, "manzils", "manzil"))
        page = assign(keys, boundaries(root, "pages", "page"))

        sajdas = {}
        sajda_parent = root.find("sajdas")
        if sajda_parent is not None:
            for el in sajda_parent.iter("sajda"):
                sajdas[(int(el.get("sura")), int(el.get("aya")))] = el.get(
                    "type", "recommended"
                )

        for v in verses:
            key = (v.surah_number, v.ayah_number)
            v.juz = juz[key]
            v.hizb_quarter = hizb[key]
            v.ruku = ruku[key]
            v.manzil = manzil[key]
            v.page = page[key]
            v.sajda = sajdas.get(key)

        await session.commit()
        print(f"metadata applied to {len(verses)} verses; sajdas: {len(sajdas)}")


if __name__ == "__main__":
    asyncio.run(run())
