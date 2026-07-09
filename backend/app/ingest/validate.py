"""Post-ingest integrity checks. Exits non-zero unless every check passes.

Run:  uv run python -m app.ingest.validate
"""

import asyncio
import sys

from sqlalchemy import func, select

from app.db.engine import get_sessionmaker
from app.db.models import Edition, HadithCollection, HadithRecord, QuranTranslation, QuranVerse, Surah
from app.retrieval.arabic import normalize_arabic

FAILURES: list[str] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(label)


# Known-text spot checks (normalized substrings so script variants don't matter)
SPOT_CHECKS = {
    (1, 1): "بسم الله الرحمن الرحيم",
    (2, 255): "الله لا اله الا هو الحي القيوم",
    (112, 1): "قل هو الله احد",
}

# Loose floor counts — dataset revisions may shift totals slightly upward
HADITH_MINIMUMS = {
    "bukhari": 7000,
    "muslim": 5000,
    "abudawud": 4500,
    "tirmidhi": 3800,
    "nasai": 5500,
    "ibnmajah": 4300,
    "malik": 1500,
    "nawawi": 40,
    "qudsi": 40,
    "dehlawi": 40,
}


async def run() -> None:
    async with get_sessionmaker()() as session:
        # --- Quran structure
        surah_count = (await session.execute(select(func.count()).select_from(Surah))).scalar()
        check(surah_count == 114, "114 surahs", f"got {surah_count}")

        verse_count = (await session.execute(select(func.count()).select_from(QuranVerse))).scalar()
        check(verse_count == 6236, "6236 verses", f"got {verse_count}")

        mismatch = (
            await session.execute(
                select(Surah.number)
                .join(QuranVerse, QuranVerse.surah_number == Surah.number)
                .group_by(Surah.number, Surah.ayah_count)
                .having(func.count() != Surah.ayah_count)
            )
        ).scalars().all()
        check(not mismatch, "per-surah ayah counts match metadata", f"mismatches: {mismatch}")

        empty_names = (
            await session.execute(select(func.count()).where(Surah.name_transliterated == ""))
        ).scalar()
        check(empty_names == 0, "surah names enriched", f"{empty_names} un-enriched")

        # --- Verse text spot checks
        for (s, a), expected in SPOT_CHECKS.items():
            row = (
                await session.execute(
                    select(QuranVerse).where(
                        QuranVerse.surah_number == s, QuranVerse.ayah_number == a
                    )
                )
            ).scalar_one_or_none()
            ok = row is not None and normalize_arabic(expected) in row.text_arabic_normalized
            check(ok, f"verse {s}:{a} text spot check")

        # --- Basmala prefixes: ayah 1 of suras 2..114 except 9
        basmala_count = (
            await session.execute(
                select(func.count()).where(
                    QuranVerse.ayah_number == 1, QuranVerse.basmala_prefix.is_not(None)
                )
            )
        ).scalar()
        check(basmala_count == 112, "basmala prefix on 112 suras", f"got {basmala_count}")
        tawbah = (
            await session.execute(
                select(QuranVerse.basmala_prefix).where(
                    QuranVerse.surah_number == 9, QuranVerse.ayah_number == 1
                )
            )
        ).scalar_one()
        check(tawbah is None, "surah 9 has no basmala")

        # --- Metadata coverage
        for col, lo, hi in [
            (QuranVerse.juz, 1, 30),
            (QuranVerse.page, 1, 604),
            (QuranVerse.hizb_quarter, 1, 240),
            (QuranVerse.manzil, 1, 7),
        ]:
            nulls = (await session.execute(select(func.count()).where(col.is_(None)))).scalar()
            bad = (
                await session.execute(select(func.count()).where((col < lo) | (col > hi)))
            ).scalar()
            check(nulls == 0 and bad == 0, f"{col.key} coverage", f"nulls={nulls} out_of_range={bad}")

        sajda_count = (
            await session.execute(select(func.count()).where(QuranVerse.sajda.is_not(None)))
        ).scalar()
        check(sajda_count in (14, 15), "sajda count 14-15", f"got {sajda_count}")

        # --- Translations
        for key in ("english_saheeh", "english_rwwad"):
            edition_id = (
                await session.execute(select(Edition.id).where(Edition.key == key))
            ).scalar_one_or_none()
            if edition_id is None:
                check(False, f"edition {key} present")
                continue
            n = (
                await session.execute(
                    select(func.count()).where(QuranTranslation.edition_id == edition_id)
                )
            ).scalar()
            check(n == 6236, f"{key}: 6236 translations", f"got {n}")

        # --- Hadith
        collections = (await session.execute(select(HadithCollection))).scalars().all()
        by_key = {c.key: c for c in collections}
        for key, minimum in HADITH_MINIMUMS.items():
            c = by_key.get(key)
            if c is None:
                check(False, f"hadith collection {key} present")
                continue
            n = (
                await session.execute(
                    select(func.count()).where(HadithRecord.collection_id == c.id)
                )
            ).scalar()
            check(n >= minimum, f"hadith {key}: >= {minimum} records", f"got {n}")

        total = (await session.execute(select(func.count()).select_from(HadithRecord))).scalar()
        eng = (
            await session.execute(
                select(func.count()).where(HadithRecord.text_english.is_not(None))
            )
        ).scalar()
        ara = (
            await session.execute(
                select(func.count()).where(HadithRecord.text_arabic.is_not(None))
            )
        ).scalar()
        check(total > 0 and eng / max(total, 1) > 0.97, "hadith english coverage > 97%", f"{eng}/{total}")
        check(total > 0 and ara / max(total, 1) > 0.90, "hadith arabic coverage > 90%", f"{ara}/{total}")

        graded = (
            await session.execute(
                select(func.count()).where(func.jsonb_array_length(HadithRecord.gradings) > 0)
            )
        ).scalar()
        print(f"[info] hadith with at least one grading: {graded}/{total}")

        # --- Editions bookkeeping (license obligations)
        editions = (await session.execute(select(Edition))).scalars().all()
        for e in editions:
            check(bool(e.attribution), f"edition {e.key}: attribution recorded")
        quranenc_missing_version = [
            e.key for e in editions if e.kind == "quran_translation" and not e.version
        ]
        if quranenc_missing_version:
            print(
                f"[warn] QuranEnc editions missing version (license asks us to display it): "
                f"{quranenc_missing_version} — fetch manually from quranenc.com edition pages"
            )

    if FAILURES:
        print(f"\n{len(FAILURES)} CHECKS FAILED: {FAILURES}")
        sys.exit(1)
    print("\nALL CHECKS PASS")


if __name__ == "__main__":
    asyncio.run(run())
