"""Query classifier + safety guard (Haiku 4.5, structured output).

FaithBrains is an educational tool, not a mufti. The guard routes every question into
one of four lanes before any answer is generated:

- educational      -> grounded answer with sources
- fatwa_seeking    -> educational context only; explicit no-ruling + refer to scholars
- sensitive_crisis -> deterministic compassionate response, no model generation
- out_of_scope     -> polite redirect

The classifier is one layer; the answer engine's system prompt independently enforces
the no-fatwa policy (defense in depth), and the API appends a disclaimer regardless.
"""

from dataclasses import dataclass

from app.ai.base import ChatProvider

CATEGORIES = ("educational", "fatwa_seeking", "sensitive_crisis", "out_of_scope")

_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": list(CATEGORIES)},
        "reason": {"type": "string"},
    },
    "required": ["category", "reason"],
    "additionalProperties": False,
}

_SYSTEM = """You classify questions sent to an Islamic educational assistant into exactly one category.

Categories:
- educational: seeking knowledge or understanding about Islam, the Quran, Hadith, history, theology, or practice in general terms. "What does the Quran say about patience?", "How do Muslims pray?", "What is riba?"
- fatwa_seeking: asking for a religious ruling applied to the asker's own life or a specific real situation — permissibility for them personally, validity of their marriage/divorce/transaction, what they personally must do. "Can I take this mortgage?", "Is my fast valid if I did X?", "Do I have to ...?". When personal circumstances drive the question, choose this even if it also has an educational side.
- sensitive_crisis: any signal of self-harm, suicide, abuse, or immediate danger to the asker or others. When in doubt between this and anything else, choose this.
- out_of_scope: unrelated to Islam or religious learning (tech support, homework, politics unrelated to religion, etc.).

Classify the user's question. Respond with the category and a one-sentence reason."""


@dataclass(frozen=True)
class Classification:
    category: str
    reason: str


async def classify(question: str, chat: ChatProvider) -> Classification:
    result = await chat.structured(
        model=chat.classifier_model,
        system=_SYSTEM,
        user=question.strip()[:2000],
        schema=_SCHEMA,
        max_tokens=300,
    )
    category = result.get("category")
    if category not in CATEGORIES:  # belt and braces; schema should prevent this
        category = "educational"
    return Classification(category=category, reason=str(result.get("reason", "")))


# Deterministic responses for lanes that must not depend on model generation.

CRISIS_RESPONSE = (
    "I'm really sorry you're going through this. I'm an educational tool and not able to "
    "give you the support you deserve right now — please reach out to someone who can: "
    "contact your local emergency services or a crisis helpline in your country, or speak "
    "to a trusted person, imam, or counselor right away. You matter, and you don't have to "
    "carry this alone. The Quran reminds us that \"Allah does not burden a soul beyond that "
    "it can bear\" (2:286) — and seeking help is itself an act of strength and faith."
)

OUT_OF_SCOPE_RESPONSE = (
    "I'm FaithBrains, an educational assistant for learning about Islam — the Quran, Hadith, "
    "and Islamic knowledge. That question is outside what I can help with. Feel free to ask "
    "me anything about the Quran, authentic hadith, or Islamic teachings."
)

STANDARD_DISCLAIMER = (
    "FaithBrains is an educational tool, not a religious authority. It does not issue fatwas "
    "or rulings. For guidance on your personal situation, please consult a qualified scholar."
)
