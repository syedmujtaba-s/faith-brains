import json
import time

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.answer import AnswerService
from app.ai.base import AIUnavailable
from app.api import schemas
from app.api.ratelimit import limit_ask, limit_search
from app.config import get_settings
from app.db.engine import get_session
from app.db.models import (
    AskLog,
    Edition,
    HadithCollection,
    HadithRecord,
    QuranTranslation,
    QuranVerse,
    Surah,
    Tafsir,
)
from app.retrieval.service import DEFAULT_TRANSLATION_KEY, SearchService

router = APIRouter()
search_service = SearchService()
answer_service = AnswerService(search=search_service)


@router.get("/health")
async def health(session: AsyncSession = Depends(get_session)) -> dict:
    verse_count = (await session.execute(select(func.count()).select_from(QuranVerse))).scalar()
    hadith_count = (await session.execute(select(func.count()).select_from(HadithRecord))).scalar()
    embedded = (
        await session.execute(
            select(func.count()).where(QuranTranslation.embedding.is_not(None))
        )
    ).scalar()
    return {
        "status": "ok",
        "verses": verse_count,
        "hadiths": hadith_count,
        "quran_embeddings": embedded,
    }


@router.get("/editions", response_model=list[schemas.EditionOut])
async def editions(session: AsyncSession = Depends(get_session)):
    return (await session.execute(select(Edition).order_by(Edition.kind, Edition.key))).scalars().all()


@router.get("/quran/surahs", response_model=list[schemas.SurahOut])
async def surahs(session: AsyncSession = Depends(get_session)):
    return (await session.execute(select(Surah).order_by(Surah.number))).scalars().all()


def _verse_out(v: QuranVerse) -> schemas.VerseOut:
    return schemas.VerseOut(
        surah=v.surah_number,
        ayah=v.ayah_number,
        reference=f"{v.surah_number}:{v.ayah_number}",
        text_uthmani=v.text_uthmani,
        text_simple=v.text_simple,
        basmala_prefix=v.basmala_prefix,
        juz=v.juz,
        page=v.page,
        sajda=v.sajda,
        translations=[
            schemas.TranslationOut(edition=t.edition.key, text=t.text, footnotes=t.footnotes)
            for t in sorted(v.translations, key=lambda t: t.edition.key)
        ],
    )


@router.get("/quran/{surah_number}", response_model=schemas.SurahDetailOut)
async def surah_detail(
    surah_number: int,
    offset: int = Query(0, ge=0),
    limit: int = Query(0, ge=0, le=300),  # 0 = all verses (long surahs should paginate)
    session: AsyncSession = Depends(get_session),
):
    surah = await session.get(Surah, surah_number)
    if surah is None:
        raise HTTPException(404, "surah not found")
    stmt = (
        select(QuranVerse)
        .options(selectinload(QuranVerse.translations).selectinload(QuranTranslation.edition))
        .where(QuranVerse.surah_number == surah_number)
        .order_by(QuranVerse.ayah_number)
        .offset(offset)
    )
    if limit:
        stmt = stmt.limit(limit)
    verses = (await session.execute(stmt)).scalars().all()
    return schemas.SurahDetailOut(
        surah=schemas.SurahOut.model_validate(surah),
        offset=offset,
        limit=limit,
        verses=[_verse_out(v) for v in verses],
    )


@router.get("/quran/{surah_number}/{ayah_number}", response_model=schemas.VerseOut)
async def verse_detail(
    surah_number: int,
    ayah_number: int,
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(QuranVerse)
        .options(selectinload(QuranVerse.translations).selectinload(QuranTranslation.edition))
        .where(
            QuranVerse.surah_number == surah_number,
            QuranVerse.ayah_number == ayah_number,
        )
    )
    verse = (await session.execute(stmt)).scalar_one_or_none()
    if verse is None:
        raise HTTPException(404, "verse not found")
    return _verse_out(verse)


@router.get("/quran/{surah_number}/{ayah_number}/tafsir", response_model=list[schemas.TafsirOut])
async def verse_tafsir(
    surah_number: int,
    ayah_number: int,
    session: AsyncSession = Depends(get_session),
):
    rows = (
        (
            await session.execute(
                select(Tafsir)
                .join(QuranVerse)
                .where(
                    QuranVerse.surah_number == surah_number,
                    QuranVerse.ayah_number == ayah_number,
                )
                .order_by(Tafsir.source_key)
            )
        )
        .scalars()
        .all()
    )
    return [
        schemas.TafsirOut(
            source_key=t.source_key, source_name=t.source_name, language=t.language, text=t.text
        )
        for t in rows
    ]


@router.get("/hadith/collections", response_model=list[schemas.HadithCollectionOut])
async def hadith_collections(session: AsyncSession = Depends(get_session)):
    stmt = (
        select(HadithCollection, func.count(HadithRecord.id))
        .join(HadithRecord, isouter=True)
        .group_by(HadithCollection.id)
        .order_by(HadithCollection.id)
    )
    rows = (await session.execute(stmt)).all()
    return [
        schemas.HadithCollectionOut(
            key=c.key, name_english=c.name_english, name_arabic=c.name_arabic, hadith_count=n
        )
        for c, n in rows
    ]


def _hadith_out(r: HadithRecord) -> schemas.HadithOut:
    return schemas.HadithOut(
        collection=r.collection.key,
        collection_name=r.collection.name_english,
        number=r.hadith_number,
        book_number=r.book_number,
        book_name=r.book_name,
        number_in_book=r.number_in_book,
        text_arabic=r.text_arabic,
        text_english=r.text_english,
        gradings=[schemas.GradingOut(**g) for g in (r.gradings or [])],
        reference_schemes=r.reference_schemes or {},
    )


@router.get("/hadith/{collection_key}", response_model=schemas.HadithListOut)
async def hadith_listing(
    collection_key: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
):
    collection = (
        await session.execute(
            select(HadithCollection).where(HadithCollection.key == collection_key)
        )
    ).scalar_one_or_none()
    if collection is None:
        raise HTTPException(404, "collection not found")
    total = (
        await session.execute(
            select(func.count()).where(HadithRecord.collection_id == collection.id)
        )
    ).scalar()
    # hadith_number is text ("2564a"); cast its numeric prefix for natural reading order
    order = func.cast(func.substring(HadithRecord.hadith_number, r"^\d+"), Integer)
    stmt = (
        select(HadithRecord)
        .options(selectinload(HadithRecord.collection))
        .where(HadithRecord.collection_id == collection.id)
        .order_by(order, HadithRecord.hadith_number)
        .offset(offset)
        .limit(limit)
    )
    records = (await session.execute(stmt)).scalars().all()
    return schemas.HadithListOut(
        collection=collection.key,
        collection_name=collection.name_english,
        total=total,
        offset=offset,
        limit=limit,
        items=[_hadith_out(r) for r in records],
    )


@router.get("/hadith/{collection_key}/{number}", response_model=schemas.HadithOut)
async def hadith_detail(
    collection_key: str,
    number: str,
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(HadithRecord)
        .join(HadithCollection)
        .options(selectinload(HadithRecord.collection))
        .where(
            HadithCollection.key == collection_key,
            HadithRecord.hadith_number == number.lower(),
        )
    )
    record = (await session.execute(stmt)).scalar_one_or_none()
    if record is None:
        raise HTTPException(404, "hadith not found")
    return _hadith_out(record)


@router.post("/ask", response_model=schemas.AskResponse, dependencies=[Depends(limit_ask)])
async def ask(
    body: schemas.AskRequest,
    session: AsyncSession = Depends(get_session),
):
    if not answer_service.chat.available:
        raise HTTPException(
            503,
            "AI answers are not configured on this server "
            "(set OPENAI_API_KEY or ANTHROPIC_API_KEY)",
        )
    started = time.monotonic()
    provider = type(answer_service.chat).__name__
    model = answer_service.chat.answer_model
    try:
        outcome = await answer_service.ask(session, body.question, scope=body.scope)
    except AIUnavailable as exc:
        session.add(
            AskLog(
                question=body.question,
                provider=provider,
                model=model,
                latency_ms=int((time.monotonic() - started) * 1000),
                status="error",
                error=str(exc)[:2000],
            )
        )
        await session.commit()
        raise HTTPException(503, f"AI answer engine unavailable: {exc}") from exc
    session.add(
        AskLog(
            question=body.question,
            category=outcome["category"],
            answer=outcome["answer"],
            sources=[
                {"type": s.get("type"), "reference": s.get("reference")}
                for s in outcome["sources"]
            ],
            provider=provider,
            model=model,
            latency_ms=int((time.monotonic() - started) * 1000),
        )
    )
    await session.commit()
    return schemas.AskResponse(question=body.question, **outcome)


@router.post("/ask/stream", dependencies=[Depends(limit_ask)])
async def ask_stream(
    body: schemas.AskRequest,
    session: AsyncSession = Depends(get_session),
):
    """SSE variant of /ask: events arrive as `data: {json}` lines —
    meta (category) -> sources -> delta* -> done (full payload), or error."""
    if not answer_service.chat.available:
        raise HTTPException(
            503,
            "AI answers are not configured on this server "
            "(set OPENAI_API_KEY or ANTHROPIC_API_KEY)",
        )
    started = time.monotonic()
    provider = type(answer_service.chat).__name__
    model = answer_service.chat.answer_model

    def sse(event: dict) -> str:
        return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    async def gen():
        outcome: dict | None = None
        try:
            async for event in answer_service.ask_stream(
                session, body.question, scope=body.scope
            ):
                if event.get("event") == "done":
                    outcome = event
                yield sse(event)
        except AIUnavailable as exc:
            yield sse({"event": "error", "detail": f"AI answer engine unavailable: {exc}"})
            session.add(
                AskLog(
                    question=body.question,
                    provider=provider,
                    model=model,
                    latency_ms=int((time.monotonic() - started) * 1000),
                    status="error",
                    error=str(exc)[:2000],
                )
            )
            await session.commit()
            return
        if outcome is not None:
            session.add(
                AskLog(
                    question=body.question,
                    category=outcome["category"],
                    answer=outcome["answer"],
                    sources=[
                        {"type": s.get("type"), "reference": s.get("reference")}
                        for s in outcome["sources"]
                    ],
                    provider=provider,
                    model=model,
                    latency_ms=int((time.monotonic() - started) * 1000),
                )
            )
            await session.commit()

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get(
    "/search", response_model=schemas.SearchResponse, dependencies=[Depends(limit_search)]
)
async def search(
    q: str = Query(..., min_length=1, max_length=500),
    scope: str = Query("all", pattern="^(all|quran|hadith)$"),
    k: int = Query(20, ge=1, le=50),
    translation: str = Query(DEFAULT_TRANSLATION_KEY),
    session: AsyncSession = Depends(get_session),
):
    outcome = await search_service.search(
        session, q, scope=scope, k=k, translation_key=translation
    )
    return schemas.SearchResponse(
        query=q,
        scope=scope,
        mode=outcome["mode"],
        signals_used=outcome["signals_used"],
        results=outcome["results"],
    )


# --- admin (token-gated) ----------------------------------------------------


async def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    configured = get_settings().admin_token
    if not configured or configured == "change-me":
        raise HTTPException(403, "Admin views are disabled — set a real ADMIN_TOKEN in .env")
    if x_admin_token != configured:
        raise HTTPException(401, "Invalid or missing X-Admin-Token header")


@router.get(
    "/admin/stats", response_model=schemas.AdminStatsOut, dependencies=[Depends(require_admin)]
)
async def admin_stats(session: AsyncSession = Depends(get_session)):
    async def count(stmt) -> int:
        return (await session.execute(stmt)).scalar() or 0

    by_category_rows = (
        await session.execute(
            select(AskLog.category, func.count()).group_by(AskLog.category)
        )
    ).all()
    avg_latency = (
        await session.execute(select(func.avg(AskLog.latency_ms)).where(AskLog.status == "ok"))
    ).scalar()
    return schemas.AdminStatsOut(
        verses=await count(select(func.count()).select_from(QuranVerse)),
        hadiths=await count(select(func.count()).select_from(HadithRecord)),
        quran_embeddings=await count(
            select(func.count()).where(QuranTranslation.embedding.is_not(None))
        ),
        hadith_embeddings=await count(
            select(func.count()).where(HadithRecord.embedding.is_not(None))
        ),
        asks_total=await count(select(func.count()).select_from(AskLog)),
        asks_by_category={str(c or "error"): n for c, n in by_category_rows},
        asks_errored=await count(select(func.count()).where(AskLog.status == "error")),
        avg_latency_ms=float(avg_latency) if avg_latency is not None else None,
    )


@router.get(
    "/admin/asks", response_model=schemas.AskLogListOut, dependencies=[Depends(require_admin)]
)
async def admin_asks(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    total = (await session.execute(select(func.count()).select_from(AskLog))).scalar() or 0
    rows = (
        (
            await session.execute(
                select(AskLog).order_by(AskLog.created_at.desc()).offset(offset).limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return schemas.AskLogListOut(
        total=total,
        items=[
            schemas.AskLogOut(
                id=r.id,
                created_at=r.created_at.isoformat(),
                question=r.question,
                category=r.category,
                answer=r.answer,
                provider=r.provider,
                model=r.model,
                latency_ms=r.latency_ms,
                status=r.status,
                error=r.error,
            )
            for r in rows
        ],
    )
