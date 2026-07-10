"""Grounded answer engine (Sonnet 5).

Flow: classify -> retrieve -> generate with the retrieved sources inlined and numbered.
The model is instructed to answer ONLY from those sources and cite them as [n]; the API
returns the same numbered source list so the frontend can render citations verbatim.
"""

import logging
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import guard
from app.ai.base import ChatProvider
from app.ai.provider import get_chat_provider
from app.content.personas import PERSONAS_BY_KEY
from app.retrieval.service import SearchService

log = logging.getLogger(__name__)

SOURCE_COUNT = 8
MAX_SOURCE_CHARS = 1500  # per-source truncation for long hadith
HISTORY_TURNS = 6  # most recent turns kept as conversation context
HISTORY_TURN_CHARS = 1000  # per-turn truncation inside the prompt

_ANSWER_SYSTEM = """You are FaithBrains, an educational assistant for learning about Islam.

Grounding rules (strict):
- Answer ONLY from the numbered sources provided in the user message. Do not bring in outside claims, rulings, or hadith not present in the sources.
- Cite every claim with the source number in square brackets, e.g. [1] or [2][3].
- If the sources are insufficient to answer, say so plainly and suggest what the user could search for instead. Never fabricate a citation.
- Quote Quran and Hadith text verbatim when quoting; do not paraphrase inside quotation marks.

Religious-authority rules (strict):
- You are not a mufti and must never issue a fatwa, personal ruling, or verdict on a person's specific situation.
- Where scholars differ, present the difference neutrally rather than picking a side.
- For anything touching a personal circumstance, explain the general teaching from the sources and direct the user to a qualified scholar for their specific case.

Style:
- Clear, respectful, and warm. Use ﷺ after the Prophet Muhammad's name.
- Concise prose; short paragraphs. No headers unless the answer is genuinely long.
- Answer in the language of the question."""

_FATWA_ADDENDUM = """

This question asks for a personal religious ruling. You MUST NOT provide one. Instead:
1. Acknowledge the question with empathy.
2. Explain the relevant general teachings found in the sources, with citations.
3. State clearly that this depends on personal circumstances you cannot judge, and that a qualified scholar or local imam should be consulted for their specific case."""


_NO_SOURCES_MESSAGE = (
    "I couldn't find relevant passages in the Quran or Hadith collections for "
    "that question. Try rephrasing it, or browse the Quran and Hadith tabs directly."
)

_CONDENSE_SYSTEM = (
    "You rewrite a conversational follow-up as one standalone question. Read the "
    "conversation, then restate the final follow-up so it can be understood with no "
    "prior context, in the same language, preserving the asker's intent. Output "
    "ONLY the rewritten question — no preamble, no quotes."
)

_CITATION_MARKER = re.compile(r"\[\d+\]")


def _persona_hint(persona: str | None) -> str:
    """Style/depth addendum for a known persona; empty string otherwise.

    Appended after the safety blocks — it must only tune voice, never rules.
    """
    p = PERSONAS_BY_KEY.get(persona or "")
    if not p:
        return ""
    return (
        "\n\nAudience adaptation (style and depth only — every grounding and "
        "religious-authority rule above still applies):\n" + p["prompt_hint"]
    )


def _transcript(history: list[dict]) -> str:
    """Recent turns as User:/Assistant: lines. Assistant turns lose their [n]
    markers — those numbers referred to a previous answer's source list and would
    collide with the fresh numbering in this turn's prompt."""
    lines = []
    for turn in history[-HISTORY_TURNS:]:
        who = "Assistant" if turn.get("role") == "assistant" else "User"
        content = _CITATION_MARKER.sub("", (turn.get("content") or "")).strip()
        lines.append(f"{who}: {content[:HISTORY_TURN_CHARS]}")
    return "\n".join(lines)


class AnswerService:
    def __init__(self, chat: ChatProvider | None = None, search: SearchService | None = None):
        self.chat = chat or get_chat_provider()
        self.search = search or SearchService()

    async def ask(
        self,
        session: AsyncSession,
        question: str,
        scope: str = "all",
        persona: str | None = None,
        history: list[dict] | None = None,
    ) -> dict:
        standalone = await self._condense(question, history)
        classification = await guard.classify(standalone, self.chat)

        if classification.category == "sensitive_crisis":
            return self._respond(classification, guard.CRISIS_RESPONSE, [])
        if classification.category == "out_of_scope":
            return self._respond(classification, guard.OUT_OF_SCOPE_RESPONSE, [])

        retrieval = await self.search.search(session, standalone, scope=scope, k=SOURCE_COUNT)
        sources = retrieval["results"]
        if not sources:
            return self._respond(classification, _NO_SOURCES_MESSAGE, [])

        system = _ANSWER_SYSTEM
        if classification.category == "fatwa_seeking":
            system += _FATWA_ADDENDUM
        system += _persona_hint(persona)

        answer = await self.chat.text(
            model=self.chat.answer_model,
            system=system,
            user=self._build_prompt(question, sources, history),
            max_tokens=8000,
            effort="medium",
        )
        return self._respond(classification, answer.strip(), sources)

    async def ask_stream(
        self,
        session: AsyncSession,
        question: str,
        scope: str = "all",
        persona: str | None = None,
        history: list[dict] | None = None,
    ):
        """Same flow as ask(), but yields event dicts as work completes:
        {"event": "meta"} -> {"event": "sources"} -> {"event": "delta"}* -> {"event": "done"}.
        The done event carries the full ask() payload so callers can log it identically.
        Deterministic lanes (crisis / out-of-scope / no sources) skip straight to done."""
        standalone = await self._condense(question, history)
        classification = await guard.classify(standalone, self.chat)
        yield {"event": "meta", "category": classification.category}

        if classification.category == "sensitive_crisis":
            yield {"event": "done", **self._respond(classification, guard.CRISIS_RESPONSE, [])}
            return
        if classification.category == "out_of_scope":
            yield {"event": "done", **self._respond(classification, guard.OUT_OF_SCOPE_RESPONSE, [])}
            return

        retrieval = await self.search.search(session, standalone, scope=scope, k=SOURCE_COUNT)
        sources = retrieval["results"]
        if not sources:
            yield {"event": "done", **self._respond(classification, _NO_SOURCES_MESSAGE, [])}
            return

        yield {"event": "sources", "sources": sources}

        system = _ANSWER_SYSTEM
        if classification.category == "fatwa_seeking":
            system += _FATWA_ADDENDUM
        system += _persona_hint(persona)

        parts: list[str] = []
        async for delta in self.chat.text_stream(
            model=self.chat.answer_model,
            system=system,
            user=self._build_prompt(question, sources, history),
            max_tokens=8000,
            effort="medium",
        ):
            parts.append(delta)
            yield {"event": "delta", "text": delta}

        yield {"event": "done", **self._respond(classification, "".join(parts).strip(), sources)}

    async def _condense(self, question: str, history: list[dict] | None) -> str:
        """Rewrite a follow-up into a standalone question for classification and
        retrieval (elliptical follow-ups like "and how did he show it?" retrieve
        nothing on their own). The original question is still what gets displayed,
        stored, and answered. Falls back to the raw question on any failure."""
        if not history:
            return question
        try:
            standalone = await self.chat.text(
                model=self.chat.classifier_model,
                system=_CONDENSE_SYSTEM,
                user=f"{_transcript(history)}\n\nFollow-up: {question.strip()}",
                max_tokens=300,
                effort="low",
            )
            standalone = standalone.strip()
            if 3 <= len(standalone) <= 2000:
                return standalone
        except Exception:  # noqa: BLE001 — condense is best-effort by design
            log.warning("condense step failed; using the raw follow-up", exc_info=True)
        return question

    def _respond(self, classification, answer: str, sources: list) -> dict:
        return {
            "category": classification.category,
            "answer": answer,
            "sources": sources,
            "disclaimer": guard.STANDARD_DISCLAIMER,
        }

    def _build_prompt(
        self, question: str, sources: list[dict], history: list[dict] | None = None
    ) -> str:
        lines = []
        if history:
            lines.append(
                "Earlier conversation (context only — answer the final question and "
                "cite ONLY the numbered sources below):"
            )
            lines.append(_transcript(history))
            lines.append("")
        lines.append("Sources:")
        for i, s in enumerate(sources, start=1):
            if s["type"] == "quran":
                text = (s.get("translation") or "").strip()[:MAX_SOURCE_CHARS]
                lines.append(
                    f"[{i}] Quran {s['reference']} (Surah {s['surah_name']}): "
                    f"“{text}” (Arabic: {s.get('arabic', '')})"
                )
            else:
                text = (s.get("english") or "").strip()[:MAX_SOURCE_CHARS]
                grades = ", ".join(
                    f"{g.get('name')}: {g.get('grade')}" for g in (s.get("gradings") or [])[:2]
                )
                grade_note = f" [Grading — {grades}]" if grades else ""
                lines.append(f"[{i}] {s['reference']}{grade_note}: “{text}”")
        lines.append("")
        lines.append(f"Question: {question.strip()}")
        return "\n".join(lines)
