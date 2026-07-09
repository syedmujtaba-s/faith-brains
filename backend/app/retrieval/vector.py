"""Vector (semantic) search signal over pgvector HNSW indexes.

Both functions filter on embedding_model: comparing a query vector against rows
embedded by a different model yields plausible-looking garbage (measured: eval
hit@10 dropped 60% -> 50% when Gemini queries hit Voyage documents), so rows from
other models are excluded rather than silently mis-ranked.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import HadithRecord, QuranTranslation


async def vector_quran(
    session: AsyncSession, embedding: list[float], edition_id: int, k: int, model: str
) -> list[tuple[int, float]]:
    """Returns [(verse_id, cosine_similarity)] best-first."""
    dist = QuranTranslation.embedding.cosine_distance(embedding)
    stmt = (
        select(QuranTranslation.verse_id, (1 - dist).label("sim"))
        .where(
            QuranTranslation.embedding.is_not(None),
            QuranTranslation.embedding_model == model,
            QuranTranslation.edition_id == edition_id,
        )
        .order_by(dist)
        .limit(k)
    )
    return [(vid, float(s)) for vid, s in (await session.execute(stmt)).all()]


async def vector_hadith(
    session: AsyncSession, embedding: list[float], k: int, model: str
) -> list[tuple[int, float]]:
    dist = HadithRecord.embedding.cosine_distance(embedding)
    stmt = (
        select(HadithRecord.id, (1 - dist).label("sim"))
        .where(
            HadithRecord.embedding.is_not(None),
            HadithRecord.embedding_model == model,
        )
        .order_by(dist)
        .limit(k)
    )
    return [(hid, float(s)) for hid, s in (await session.execute(stmt)).all()]
