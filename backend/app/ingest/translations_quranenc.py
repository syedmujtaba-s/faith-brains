"""Import QuranEnc English translations (verbatim — license forbids any edit).

Run after quran_tanzil:  uv run python -m app.ingest.translations_quranenc
"""

import asyncio
import json

from sqlalchemy import delete, select

from app.db.engine import get_sessionmaker
from app.db.models import Edition, QuranTranslation, QuranVerse
from app.ingest.common import RAW, sha256_file, upsert_edition

EDITIONS = {
    "english_saheeh": {
        "name": "Saheeh International",
        "author": "Saheeh International",
    },
    "english_rwwad": {
        "name": "Rowwad Translation Center",
        "author": "Rowwad Translation Center",
    },
}


async def import_edition(session, key: str) -> None:
    path = RAW / "quranenc" / f"{key}.json"
    if not path.exists():
        raise SystemExit(f"missing {path} — run scripts/download_sources.py first")
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload["rows"]
    if len(rows) != 6236:
        raise SystemExit(f"{key}: expected 6236 rows, got {len(rows)}")

    edition = await upsert_edition(
        session,
        key=key,
        kind="quran_translation",
        name=EDITIONS[key]["name"],
        language="en",
        author=EDITIONS[key]["author"],
        source_url=f"https://quranenc.com/en/browse/{key}",
        license_name="QuranEnc terms: verbatim, attributed, version displayed",
        attribution=f"{EDITIONS[key]['name']} translation via QuranEnc.com",
        version=payload.get("version"),
        checksum_sha256=sha256_file(path),
    )

    verse_ids = {
        (s, a): vid
        for vid, s, a in (
            await session.execute(
                select(QuranVerse.id, QuranVerse.surah_number, QuranVerse.ayah_number)
            )
        ).all()
    }

    await session.execute(delete(QuranTranslation).where(QuranTranslation.edition_id == edition.id))

    objects = []
    for row in rows:
        vkey = (int(row["sura"]), int(row["aya"]))
        vid = verse_ids.get(vkey)
        if vid is None:
            raise SystemExit(f"{key}: no verse for {vkey}")
        text = (row.get("translation") or "").strip()
        if not text:
            raise SystemExit(f"{key}: empty translation at {vkey}")
        footnotes = (row.get("footnotes") or "").strip() or None
        objects.append(
            QuranTranslation(verse_id=vid, edition_id=edition.id, text=text, footnotes=footnotes)
        )
    session.add_all(objects)
    print(f"{key}: imported {len(objects)} verse translations (version={payload.get('version')})")


async def run() -> None:
    async with get_sessionmaker()() as session:
        for key in EDITIONS:
            await import_edition(session, key)
        await session.commit()


if __name__ == "__main__":
    asyncio.run(run())
