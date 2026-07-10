"""Anonymous learner endpoints: saved items + learning paths with progress.

Identity is a client-minted UUID in the X-Session-Id header (no accounts, no
belief profiling). A future auth layer can claim learners.session_id rows.
"""

import re
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import schemas
from app.content.learning_paths import PATHS, PATHS_BY_KEY
from app.content.personas import PERSONAS
from app.db.engine import get_session
from app.db.models import (
    Conversation,
    Edition,
    HadithCollection,
    HadithRecord,
    Learner,
    Message,
    PathProgress,
    QuranTranslation,
    QuranVerse,
    SavedItem,
)
from app.retrieval.service import DEFAULT_TRANSLATION_KEY

router = APIRouter()

_SESSION_RE = re.compile(r"[A-Za-z0-9-]{8,64}")


async def get_learner(
    x_session_id: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> Learner:
    if not x_session_id or not _SESSION_RE.fullmatch(x_session_id):
        raise HTTPException(400, "X-Session-Id header required (client-generated UUID)")
    learner = (
        await session.execute(select(Learner).where(Learner.session_id == x_session_id))
    ).scalar_one_or_none()
    if learner is None:
        # Upsert handles two first-requests racing on the same fresh session id
        await session.execute(
            pg_insert(Learner)
            .values(session_id=x_session_id)
            .on_conflict_do_nothing(index_elements=["session_id"])
        )
        learner = (
            await session.execute(select(Learner).where(Learner.session_id == x_session_id))
        ).scalar_one()
    learner.last_seen_at = datetime.now(UTC)
    await session.commit()
    return learner


async def get_learner_optional(
    x_session_id: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> Learner | None:
    if not x_session_id or not _SESSION_RE.fullmatch(x_session_id):
        return None
    return await get_learner(x_session_id, session)


# -- personas --------------------------------------------------------------------


@router.get("/personas", response_model=list[schemas.PersonaOut])
async def list_personas():
    """Public persona catalogue (labels, suggested questions, recommended paths).
    prompt_hint stays server-side."""
    return [
        schemas.PersonaOut(
            key=p["key"],
            label=p["label"],
            tagline=p["tagline"],
            suggested_questions=p["suggested_questions"],
            recommended_paths=p["recommended_paths"],
        )
        for p in PERSONAS
    ]


@router.put("/learner/persona", response_model=schemas.LearnerOut)
async def set_persona(
    body: schemas.LearnerPersonaIn,
    learner: Learner = Depends(get_learner),
    session: AsyncSession = Depends(get_session),
):
    learner.persona = body.persona
    await session.commit()
    return schemas.LearnerOut(session_id=learner.session_id, persona=learner.persona)


# -- saved items ---------------------------------------------------------------


@router.get("/saved", response_model=list[schemas.SavedItemOut])
async def list_saved(
    learner: Learner = Depends(get_learner),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        await session.execute(
            select(SavedItem)
            .where(SavedItem.learner_id == learner.id)
            .order_by(SavedItem.created_at.desc())
        )
    ).scalars()
    return [schemas.SavedItemOut(kind=r.kind, reference=r.reference) for r in rows]


@router.post("/saved", response_model=list[schemas.SavedItemOut])
async def save_item(
    body: schemas.SavedItemIn,
    learner: Learner = Depends(get_learner),
    session: AsyncSession = Depends(get_session),
):
    await session.execute(
        pg_insert(SavedItem)
        .values(learner_id=learner.id, kind=body.kind, reference=body.reference.strip())
        .on_conflict_do_nothing(constraint="uq_saved_learner_ref")
    )
    await session.commit()
    return await list_saved(learner, session)


@router.delete("/saved", response_model=list[schemas.SavedItemOut])
async def unsave_item(
    kind: str = Query(..., pattern="^(quran|hadith)$"),
    reference: str = Query(..., min_length=1, max_length=100),
    learner: Learner = Depends(get_learner),
    session: AsyncSession = Depends(get_session),
):
    await session.execute(
        delete(SavedItem).where(
            SavedItem.learner_id == learner.id,
            SavedItem.kind == kind,
            SavedItem.reference == reference,
        )
    )
    await session.commit()
    return await list_saved(learner, session)


# -- conversations ----------------------------------------------------------------


async def _owned_conversation(
    session: AsyncSession, learner: Learner, conversation_id: int
) -> Conversation:
    conversation = (
        await session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.learner_id == learner.id,
            )
        )
    ).scalar_one_or_none()
    if conversation is None:
        raise HTTPException(404, "conversation not found")
    return conversation


@router.get("/conversations", response_model=list[schemas.ConversationSummaryOut])
async def list_conversations(
    learner: Learner = Depends(get_learner),
    session: AsyncSession = Depends(get_session),
):
    msg_count = (
        select(func.count())
        .where(Message.conversation_id == Conversation.id)
        .scalar_subquery()
    )
    rows = (
        await session.execute(
            select(Conversation, msg_count)
            .where(Conversation.learner_id == learner.id)
            .order_by(Conversation.updated_at.desc())
            .limit(30)
        )
    ).all()
    return [
        schemas.ConversationSummaryOut(
            id=c.id,
            title=c.title,
            updated_at=c.updated_at.isoformat(),
            message_count=n,
        )
        for c, n in rows
    ]


@router.get("/conversations/{conversation_id}", response_model=schemas.ConversationDetailOut)
async def conversation_detail(
    conversation_id: int,
    learner: Learner = Depends(get_learner),
    session: AsyncSession = Depends(get_session),
):
    conversation = await _owned_conversation(session, learner, conversation_id)
    messages = (
        (
            await session.execute(
                select(Message)
                .where(Message.conversation_id == conversation.id)
                .order_by(Message.id)
            )
        )
        .scalars()
        .all()
    )
    return schemas.ConversationDetailOut(
        id=conversation.id,
        title=conversation.title,
        messages=[
            schemas.MessageOut(
                role=m.role,
                content=m.content,
                category=m.category,
                sources=m.sources or [],
                created_at=m.created_at.isoformat(),
            )
            for m in messages
        ],
    )


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: int,
    learner: Learner = Depends(get_learner),
    session: AsyncSession = Depends(get_session),
):
    conversation = await _owned_conversation(session, learner, conversation_id)
    await session.execute(delete(Message).where(Message.conversation_id == conversation.id))
    await session.delete(conversation)
    await session.commit()


# -- learning paths --------------------------------------------------------------


async def _completed_steps(session: AsyncSession, learner: Learner | None, path_key: str) -> set[str]:
    if learner is None:
        return set()
    rows = (
        await session.execute(
            select(PathProgress.step_key).where(
                PathProgress.learner_id == learner.id, PathProgress.path_key == path_key
            )
        )
    ).scalars()
    return set(rows)


@router.get("/learn/paths", response_model=list[schemas.PathSummaryOut])
async def list_paths(
    learner: Learner | None = Depends(get_learner_optional),
    session: AsyncSession = Depends(get_session),
):
    out = []
    for p in PATHS:
        done = await _completed_steps(session, learner, p["key"])
        out.append(
            schemas.PathSummaryOut(
                key=p["key"],
                title=p["title"],
                description=p["description"],
                step_count=len(p["steps"]),
                completed_count=len(done & {s["key"] for s in p["steps"]}),
            )
        )
    return out


async def _hydrate_step(session: AsyncSession, step: dict, done: set[str]) -> schemas.PathStepOut:
    kind, ref = step["kind"], step["reference"]
    arabic = text = grading = None
    if kind == "quran":
        s, a = (int(x) for x in ref.split(":"))
        row = (
            await session.execute(
                select(QuranVerse.text_uthmani, QuranTranslation.text)
                .join(QuranTranslation, QuranTranslation.verse_id == QuranVerse.id)
                .join(Edition, Edition.id == QuranTranslation.edition_id)
                .where(
                    QuranVerse.surah_number == s,
                    QuranVerse.ayah_number == a,
                    Edition.key == DEFAULT_TRANSLATION_KEY,
                )
            )
        ).first()
        if row:
            arabic, text = row
    else:
        coll, num = ref.rsplit(" ", 1)
        rec = (
            await session.execute(
                select(HadithRecord)
                .join(HadithCollection)
                .where(HadithCollection.key == coll, HadithRecord.hadith_number == num)
            )
        ).scalar_one_or_none()
        if rec:
            text = rec.text_english
            g = (rec.gradings or [None])[0]
            grading = f"{g.get('name')}: {g.get('grade')}" if isinstance(g, dict) else None
    return schemas.PathStepOut(
        key=step["key"],
        title=step["title"],
        kind=kind,
        reference=ref,
        arabic=arabic,
        text=text,
        grading=grading,
        completed=step["key"] in done,
    )


@router.get("/learn/paths/{path_key}", response_model=schemas.PathDetailOut)
async def path_detail(
    path_key: str,
    learner: Learner | None = Depends(get_learner_optional),
    session: AsyncSession = Depends(get_session),
):
    p = PATHS_BY_KEY.get(path_key)
    if p is None:
        raise HTTPException(404, "learning path not found")
    done = await _completed_steps(session, learner, path_key)
    steps = [await _hydrate_step(session, s, done) for s in p["steps"]]
    return schemas.PathDetailOut(
        key=p["key"], title=p["title"], description=p["description"], steps=steps
    )


@router.post("/learn/paths/{path_key}/steps/{step_key}/complete", response_model=schemas.PathProgressOut)
async def complete_step(
    path_key: str,
    step_key: str,
    learner: Learner = Depends(get_learner),
    session: AsyncSession = Depends(get_session),
):
    p = PATHS_BY_KEY.get(path_key)
    if p is None or step_key not in {s["key"] for s in p["steps"]}:
        raise HTTPException(404, "unknown path or step")
    await session.execute(
        pg_insert(PathProgress)
        .values(learner_id=learner.id, path_key=path_key, step_key=step_key)
        .on_conflict_do_nothing(constraint="uq_progress_step")
    )
    await session.commit()
    done = await _completed_steps(session, learner, path_key)
    return schemas.PathProgressOut(
        path_key=path_key, completed=sorted(done), step_count=len(p["steps"])
    )
