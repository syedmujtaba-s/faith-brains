"""Tests for POST /ask — classifier routing, grounding, and safety lanes.

Uses a FakeClaude so no network is touched; retrieval runs against the seeded test DB.
"""

import json

import pytest

from app.ai import guard
from app.ai.answer import AnswerService
from app.ai.claude import ClaudeChat
from app.api import routes

pytestmark = pytest.mark.integration


class FakeClaude(ClaudeChat):
    def __init__(self, category: str = "educational", answer_text: str = "Grounded answer [1]."):
        super().__init__(api_key="fake-key")
        self.category = category
        self.answer_text = answer_text
        self.structured_calls: list[dict] = []
        self.text_calls: list[dict] = []

    async def structured(self, **kwargs) -> dict:
        self.structured_calls.append(kwargs)
        return {"category": self.category, "reason": "test classification"}

    async def text(self, **kwargs) -> str:
        self.text_calls.append(kwargs)
        return self.answer_text

    async def text_stream(self, **kwargs):
        self.text_calls.append(kwargs)
        mid = max(1, len(self.answer_text) // 2)
        yield self.answer_text[:mid]
        yield self.answer_text[mid:]


@pytest.fixture()
def fake_ask(monkeypatch):
    """Install an AnswerService backed by FakeClaude; returns the fake for assertions."""

    def _install(category: str = "educational", answer_text: str = "Grounded answer [1].") -> FakeClaude:
        fake = FakeClaude(category=category, answer_text=answer_text)
        monkeypatch.setattr(
            routes, "answer_service", AnswerService(chat=fake, search=routes.search_service)
        )
        return fake

    return _install


async def test_ask_educational_grounded(client, fake_ask):
    fake = fake_ask(category="educational")
    resp = await client.post(
        "/api/v1/ask", json={"question": "What does the Quran say about drowsiness and sleep?"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["category"] == "educational"
    assert body["answer"] == "Grounded answer [1]."
    assert body["disclaimer"]
    assert any(s["reference"] == "2:255" for s in body["sources"])

    # The generation prompt must contain the numbered sources and the question
    assert len(fake.text_calls) == 1
    prompt = fake.text_calls[0]["user"]
    assert "[1]" in prompt and "Question:" in prompt
    assert "drowsiness" in prompt.lower()


async def test_ask_fatwa_seeking_gets_no_ruling_addendum(client, fake_ask):
    fake = fake_ask(category="fatwa_seeking")
    resp = await client.post(
        "/api/v1/ask", json={"question": "Is it permissible for me to delay my prayer at work?"}
    )
    assert resp.status_code == 200
    assert resp.json()["category"] == "fatwa_seeking"
    assert len(fake.text_calls) == 1
    system = fake.text_calls[0]["system"]
    assert "MUST NOT provide one" in system


async def test_ask_crisis_is_deterministic_and_skips_generation(client, fake_ask):
    fake = fake_ask(category="sensitive_crisis")
    resp = await client.post("/api/v1/ask", json={"question": "I can't go on anymore"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["category"] == "sensitive_crisis"
    assert body["answer"] == guard.CRISIS_RESPONSE
    assert body["sources"] == []
    assert fake.text_calls == []  # no model generation on the crisis lane


async def test_ask_out_of_scope(client, fake_ask):
    fake = fake_ask(category="out_of_scope")
    resp = await client.post("/api/v1/ask", json={"question": "Fix my python code please"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == guard.OUT_OF_SCOPE_RESPONSE
    assert fake.text_calls == []


async def test_ask_no_matching_sources(client, fake_ask):
    fake = fake_ask(category="educational")
    resp = await client.post(
        "/api/v1/ask", json={"question": "zzxqy flurbish nonexistent gibberish"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "couldn't find" in body["answer"]
    assert body["sources"] == []
    assert fake.text_calls == []  # never generate without grounding material


async def test_ask_without_api_key_returns_503(client, monkeypatch):
    monkeypatch.setattr(
        routes, "answer_service", AnswerService(chat=ClaudeChat(api_key=""), search=routes.search_service)
    )
    resp = await client.post("/api/v1/ask", json={"question": "What is patience in Islam?"})
    assert resp.status_code == 503
    assert "API_KEY" in resp.json()["detail"]


async def test_provider_selection():
    from app.ai.claude import ClaudeChat as CC
    from app.ai.openai_chat import OpenAIChat

    assert OpenAIChat(api_key="").available is False
    assert OpenAIChat(api_key="sk-test").available is True
    assert CC(api_key="").available is False
    # both providers satisfy the shared protocol surface
    for provider in (OpenAIChat(api_key="x"), CC(api_key="x")):
        assert provider.answer_model and provider.classifier_model


async def test_gemini_embedder_formatting_and_selection(monkeypatch):
    from app.ai.embeddings import GeminiEmbedder, VoyageEmbedder, get_embedder
    from app.config import get_settings

    e = GeminiEmbedder(api_key="g-test")
    assert e.available and e.dim == 1024
    assert e.format_text("patience", "query") == "task: search result | query: patience"
    assert e.format_text("verse text", "document") == "title: none | text: verse text"

    settings = get_settings()
    monkeypatch.setattr(settings, "embedding_provider", "auto")
    monkeypatch.setattr(settings, "gemini_api_key", "g-test")
    assert isinstance(get_embedder(), GeminiEmbedder)
    monkeypatch.setattr(settings, "gemini_api_key", "")
    assert isinstance(get_embedder(), VoyageEmbedder)
    monkeypatch.setattr(settings, "embedding_provider", "voyage")
    monkeypatch.setattr(settings, "gemini_api_key", "g-test")
    assert isinstance(get_embedder(), VoyageEmbedder)


async def test_ask_validates_question_length(client, fake_ask):
    fake_ask()
    resp = await client.post("/api/v1/ask", json={"question": "hi"})
    assert resp.status_code == 422


async def test_ask_with_persona_appends_style_hint(client, fake_ask):
    fake = fake_ask(category="educational")
    resp = await client.post(
        "/api/v1/ask",
        json={
            "question": "What does the Quran say about drowsiness and sleep?",
            "persona": "new_muslim",
        },
    )
    assert resp.status_code == 200
    system = fake.text_calls[0]["system"]
    assert "someone new to Islam" in system
    # Safety blocks must remain intact ahead of any audience tuning
    assert "Answer ONLY from the numbered sources" in system
    assert "never issue a fatwa" in system


async def test_ask_without_persona_has_no_audience_block(client, fake_ask):
    fake = fake_ask(category="educational")
    resp = await client.post(
        "/api/v1/ask", json={"question": "What does the Quran say about drowsiness and sleep?"}
    )
    assert resp.status_code == 200
    assert "Audience adaptation" not in fake.text_calls[0]["system"]


async def test_ask_rejects_unknown_persona(client, fake_ask):
    fake_ask()
    resp = await client.post(
        "/api/v1/ask", json={"question": "What is patience in Islam?", "persona": "wizard"}
    )
    assert resp.status_code == 422


async def test_fatwa_addendum_precedes_persona_hint(client, fake_ask):
    fake = fake_ask(category="fatwa_seeking")
    resp = await client.post(
        "/api/v1/ask",
        json={
            "question": "Is it permissible for me to delay my prayer at work?",
            "persona": "learner",
        },
    )
    assert resp.status_code == 200
    system = fake.text_calls[0]["system"]
    assert system.index("MUST NOT provide one") < system.index("Audience adaptation")


async def _sse_events(client, question: str, **extra) -> list[dict]:
    events = []
    async with client.stream(
        "POST", "/api/v1/ask/stream", json={"question": question, **extra}
    ) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        async for line in resp.aiter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[len("data: "):]))
    return events


async def test_ask_stream_event_sequence_and_content(client, fake_ask):
    fake_ask(category="educational")
    events = await _sse_events(client, "What does the Quran say about drowsiness and sleep?")
    kinds = [e["event"] for e in events]
    assert kinds[0] == "meta" and kinds[-1] == "done"
    assert "sources" in kinds and "delta" in kinds
    deltas = "".join(e["text"] for e in events if e["event"] == "delta")
    done = events[-1]
    assert deltas == "Grounded answer [1]."
    assert done["answer"] == "Grounded answer [1]."
    assert done["disclaimer"]
    assert any(s["reference"] == "2:255" for s in done["sources"])


async def test_ask_stream_carries_persona_hint(client, fake_ask):
    fake = fake_ask(category="educational")
    events = await _sse_events(
        client, "What does the Quran say about drowsiness and sleep?", persona="student"
    )
    assert events[-1]["event"] == "done"
    system = fake.text_calls[0]["system"]
    assert "student of knowledge" in system
    assert "Answer ONLY from the numbered sources" in system


async def test_ask_stream_crisis_is_deterministic(client, fake_ask):
    fake = fake_ask(category="sensitive_crisis")
    events = await _sse_events(client, "I can't go on anymore")
    assert [e["event"] for e in events] == ["meta", "done"]
    assert events[-1]["answer"] == guard.CRISIS_RESPONSE
    assert fake.text_calls == []  # crisis lane must never hit the model


async def test_surah_pagination(client):
    full = (await client.get("/api/v1/quran/2")).json()
    assert len(full["verses"]) >= 2
    page = (await client.get("/api/v1/quran/2?offset=1&limit=1")).json()
    assert page["offset"] == 1 and page["limit"] == 1
    assert len(page["verses"]) == 1
    assert page["verses"][0]["ayah"] == full["verses"][1]["ayah"]
