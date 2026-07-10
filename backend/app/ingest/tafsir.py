"""Ingest per-verse tafsir from the spa5k/tafsir_api CDN dataset (jsDelivr).

Default edition: Tafsir Ibn Kathir (abridged, English). NOTE (docs/licensing.md):
English tafsir translations carry the same unresolved-translation-rights caveat
as the hadith corpus — fine for private beta, clear before public launch.

Run:  uv run python -m app.ingest.tafsir [edition-slug]
"""

import asyncio
import sys

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.engine import get_sessionmaker
from app.db.models import QuranVerse, Tafsir

_CDN = "https://cdn.jsdelivr.net/gh/spa5k/tafsir_api@main/tafsir"
DEFAULT_MATCH = ("ibn kathir", "en")  # (name substring, language)


async def pick_edition(client: httpx.AsyncClient, slug: str | None) -> dict:
    editions = (await client.get(f"{_CDN}/editions.json")).json()
    if slug:
        for e in editions:
            if e.get("slug") == slug:
                return e
        raise SystemExit(f"edition slug '{slug}' not found; available: "
                         + ", ".join(e.get("slug", "?") for e in editions))
    name_part, lang = DEFAULT_MATCH
    for e in editions:
        if e.get("language_name", "").lower().startswith(lang) and name_part in e.get("name", "").lower():
            return e
    raise SystemExit(f"no edition matching {DEFAULT_MATCH}; check {_CDN}/editions.json")


async def run(slug: str | None = None) -> None:
    async with httpx.AsyncClient(timeout=60) as client:
        edition = await pick_edition(client, slug)
        source_key = edition["slug"]
        source_name = edition["name"]
        language = edition.get("language_name", "english")
        print(f"ingesting tafsir: {source_name} ({source_key}, {language})")

        async with get_sessionmaker()() as session:
            verse_ids = {
                (s, a): vid
                for vid, s, a in (
                    await session.execute(
                        select(QuranVerse.id, QuranVerse.surah_number, QuranVerse.ayah_number)
                    )
                ).all()
            }
            total = 0
            for surah in range(1, 115):
                resp = await client.get(f"{_CDN}/{source_key}/{surah}.json")
                if resp.status_code != 200:
                    print(f"  surah {surah}: HTTP {resp.status_code} — skipped")
                    continue
                payload = resp.json()
                # per-surah file is a bare list of {surah, ayah, text}; older forks wrap it
                ayahs = payload.get("ayahs", []) if isinstance(payload, dict) else payload
                rows = []
                for a in ayahs:
                    vid = verse_ids.get((a.get("surah"), a.get("ayah")))
                    text = (a.get("text") or "").strip()
                    if vid is None or not text:
                        continue
                    rows.append(
                        {
                            "verse_id": vid,
                            "source_key": source_key,
                            "source_name": source_name,
                            "language": language,
                            "text": text,
                        }
                    )
                if rows:
                    stmt = pg_insert(Tafsir).values(rows).on_conflict_do_nothing(
                        constraint="uq_tafsir_verse_source"
                    )
                    await session.execute(stmt)
                    await session.commit()
                    total += len(rows)
                if surah % 20 == 0:
                    print(f"  through surah {surah}: {total} rows")
            print(f"tafsir ingest complete: {total} rows for {source_key}")


if __name__ == "__main__":
    asyncio.run(run(sys.argv[1] if len(sys.argv) > 1 else None))
