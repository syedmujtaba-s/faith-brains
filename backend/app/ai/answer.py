"""Grounded answer engine (Sonnet 5).

Flow: classify -> retrieve -> generate with the retrieved sources inlined and numbered.
The model is instructed to answer ONLY from those sources and cite them as [n]; the API
returns the same numbered source list so the frontend can render citations verbatim.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import guard
from app.ai.base import ChatProvider
from app.ai.provider import get_chat_provider
from app.retrieval.service import SearchService

log = logging.getLogger(__name__)

SOURCE_COUNT = 8
MAX_SOURCE_CHARS = 1500  # per-source truncation for long hadith

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


class AnswerService:
    def __init__(self, chat: ChatProvider | None = None, search: SearchService | None = None):
        self.chat = chat or get_chat_provider()
        self.search = search or SearchService()

    async def ask(self, session: AsyncSession, question: str, scope: str = "all") -> dict:
        classification = await guard.classify(question, self.chat)

        if classification.category == "sensitive_crisis":
            return self._respond(classification, guard.CRISIS_RESPONSE, [])
        if classification.category == "out_of_scope":
            return self._respond(classification, guard.OUT_OF_SCOPE_RESPONSE, [])

        retrieval = await self.search.search(session, question, scope=scope, k=SOURCE_COUNT)
        sources = retrieval["results"]
        if not sources:
            return self._respond(
                classification,
                "I couldn't find relevant passages in the Quran or Hadith collections for "
                "that question. Try rephrasing it, or browse the Quran and Hadith tabs directly.",
                [],
            )

        system = _ANSWER_SYSTEM
        if classification.category == "fatwa_seeking":
            system += _FATWA_ADDENDUM

        answer = await self.chat.text(
            model=self.chat.answer_model,
            system=system,
            user=self._build_prompt(question, sources),
            max_tokens=8000,
            effort="medium",
        )
        return self._respond(classification, answer.strip(), sources)

    def _respond(self, classification, answer: str, sources: list) -> dict:
        return {
            "category": classification.category,
            "answer": answer,
            "sources": sources,
            "disclaimer": guard.STANDARD_DISCLAIMER,
        }

    def _build_prompt(self, question: str, sources: list[dict]) -> str:
        lines = ["Sources:"]
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
