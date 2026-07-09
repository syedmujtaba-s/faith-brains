"""Lexical search signals: English full-text (tsvector) and Arabic trigram substring."""

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import HadithRecord, QuranTranslation, QuranVerse


async def fulltext_quran(
    session: AsyncSession, query: str, edition_id: int, k: int
) -> list[tuple[int, float]]:
    """Returns [(verse_id, rank)] best-first."""
    tsq = func.websearch_to_tsquery("english", query)
    stmt = (
        select(QuranTranslation.verse_id, func.ts_rank_cd(QuranTranslation.tsv, tsq).label("r"))
        .where(QuranTranslation.tsv.op("@@")(tsq), QuranTranslation.edition_id == edition_id)
        .order_by(sa.desc("r"))
        .limit(k)
    )
    return [(vid, float(r)) for vid, r in (await session.execute(stmt)).all()]


async def fulltext_hadith(session: AsyncSession, query: str, k: int) -> list[tuple[int, float]]:
    """Returns [(hadith_record_id, rank)] best-first."""
    tsq = func.websearch_to_tsquery("english", query)
    stmt = (
        select(HadithRecord.id, func.ts_rank_cd(HadithRecord.tsv, tsq).label("r"))
        .where(HadithRecord.tsv.op("@@")(tsq))
        .order_by(sa.desc("r"))
        .limit(k)
    )
    return [(hid, float(r)) for hid, r in (await session.execute(stmt)).all()]


async def arabic_quran(
    session: AsyncSession, normalized_query: str, k: int
) -> list[tuple[int, float]]:
    """Substring match on normalized Arabic, ranked by trigram similarity. [(verse_id, sim)]."""
    sim = func.similarity(QuranVerse.text_arabic_normalized, normalized_query)
    stmt = (
        select(QuranVerse.id, sim.label("s"))
        .where(QuranVerse.text_arabic_normalized.contains(normalized_query, autoescape=True))
        .order_by(sa.desc("s"))
        .limit(k)
    )
    return [(vid, float(s)) for vid, s in (await session.execute(stmt)).all()]


async def arabic_hadith(
    session: AsyncSession, normalized_query: str, k: int
) -> list[tuple[int, float]]:
    sim = func.similarity(HadithRecord.text_arabic_normalized, normalized_query)
    stmt = (
        select(HadithRecord.id, sim.label("s"))
        .where(HadithRecord.text_arabic_normalized.contains(normalized_query, autoescape=True))
        .order_by(sa.desc("s"))
        .limit(k)
    )
    return [(hid, float(s)) for hid, s in (await session.execute(stmt)).all()]
