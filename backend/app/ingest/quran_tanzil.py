"""Import Quran Arabic text from Tanzil XML (uthmani + simple scripts).

Creates surah stubs (Arabic name only — quran_metadata.py enriches them) and all 6236
verses. Tanzil stores the basmala as a `bismillah` attribute on ayah 1, so verse text is
already clean; we keep the attribute verbatim in basmala_prefix.

Run after download_sources.py:  uv run python -m app.ingest.quran_tanzil
"""

import asyncio
import xml.etree.ElementTree as ET

from sqlalchemy import delete, select

from app.db.engine import get_sessionmaker
from app.db.models import QuranTranslation, QuranVerse, Surah
from app.ingest.common import RAW, sha256_file, upsert_edition
from app.retrieval.arabic import normalize_arabic

UTHMANI = RAW / "tanzil" / "quran-uthmani.xml"
SIMPLE = RAW / "tanzil" / "quran-simple.xml"


def parse_tanzil(path) -> dict[tuple[int, int], dict]:
    """{(surah, ayah): {"text": ..., "bismillah": ...}} plus surah names in key (0, n)."""
    root = ET.parse(path).getroot()
    out: dict = {"verses": {}, "surah_names": {}}
    for sura in root.iter("sura"):
        s = int(sura.get("index"))
        out["surah_names"][s] = sura.get("name")
        for aya in sura.iter("aya"):
            a = int(aya.get("index"))
            out["verses"][(s, a)] = {
                "text": aya.get("text"),
                "bismillah": aya.get("bismillah"),
            }
    return out


async def run() -> None:
    for path in (UTHMANI, SIMPLE):
        if not path.exists():
            raise SystemExit(f"missing {path} — run scripts/download_sources.py first")

    uthmani = parse_tanzil(UTHMANI)
    simple = parse_tanzil(SIMPLE)
    if set(uthmani["verses"]) != set(simple["verses"]):
        raise SystemExit("uthmani and simple scripts disagree on verse keys — aborting")

    async with get_sessionmaker()() as session:
        await upsert_edition(
            session,
            key="tanzil_uthmani",
            kind="quran_text",
            name="Tanzil Quran Text (Uthmani)",
            language="ar",
            source_url="https://tanzil.net",
            license_name="Tanzil terms: verbatim redistribution with attribution",
            attribution="Quran text courtesy of the Tanzil Project (tanzil.net)",
            version="1.1",
            checksum_sha256=sha256_file(UTHMANI),
        )

        # Full reimport: translations reference verses, so this only works pre-translation
        # import or via cascade order translations -> verses.
        await session.execute(delete(QuranTranslation))
        await session.execute(delete(QuranVerse))

        existing_surahs = {
            s.number: s for s in (await session.execute(select(Surah))).scalars().all()
        }
        counts: dict[int, int] = {}
        for s, _a in uthmani["verses"]:
            counts[s] = counts.get(s, 0) + 1
        for s in range(1, 115):
            name_ar = uthmani["surah_names"][s]
            if s in existing_surahs:
                existing_surahs[s].name_arabic = name_ar
                existing_surahs[s].ayah_count = counts[s]
            else:
                session.add(
                    Surah(
                        number=s,
                        name_arabic=name_ar,
                        name_english="",
                        name_transliterated="",
                        revelation_place="",
                        ayah_count=counts[s],
                    )
                )
        await session.flush()

        verses = []
        for (s, a), u in sorted(uthmani["verses"].items()):
            text_simple = simple["verses"][(s, a)]["text"]
            verses.append(
                QuranVerse(
                    surah_number=s,
                    ayah_number=a,
                    text_uthmani=u["text"],
                    text_simple=text_simple,
                    text_arabic_normalized=normalize_arabic(text_simple),
                    basmala_prefix=u["bismillah"],
                )
            )
        session.add_all(verses)
        await session.commit()
        print(f"imported {len(verses)} verses across {len(counts)} surahs")


if __name__ == "__main__":
    asyncio.run(run())
