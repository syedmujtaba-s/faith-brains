"""Tests for multi-turn conversations: persistence, history threading, ownership."""

import json

import pytest

from app.ai.answer import AnswerService
from app.ai.claude import ClaudeChat
from app.api import routes

pytestmark = pytest.mark.integration

QUESTION = "What does the Quran say about drowsiness and sleep?"


class FakeChat(ClaudeChat):
    """Offline provider: canned classification + answer. The condense call (its
    system prompt starts with "You rewrite") returns a retrievable standalone
    question so follow-up turns still find sources in the seeded test DB."""

    def __init__(self, category: str = "educational", answer_text: str = "Grounded answer [1]."):
        super().__init__(api_key="fake-key")
        self.category = category
        self.answer_text = answer_text
        self.text_calls: list[dict] = []

    async def structured(self, **kwargs) -> dict:
        return {"category": self.category, "reason": "test classification"}

    async def text(self, **kwargs) -> str:
        self.text_calls.append(kwargs)
        if kwargs["system"].startswith("You rewrite"):
            return QUESTION  # condensed standalone question
        return self.answer_text

    async def text_stream(self, **kwargs):
        self.text_calls.append(kwargs)
        yield self.answer_text


@pytest.fixture()
def fake_chat(monkeypatch):
    def _install(**kw) -> FakeChat:
        fake = FakeChat(**kw)
        monkeypatch.setattr(
            routes, "answer_service", AnswerService(chat=fake, search=routes.search_service)
        )
        return fake

    return _install


async def _stream(client, payload: dict, headers: dict | None = None) -> list[dict]:
    events = []
    async with client.stream(
        "POST", "/api/v1/ask/stream", json=payload, headers=headers or {}
    ) as resp:
        assert resp.status_code == 200
        async for line in resp.aiter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[len("data: "):]))
    return events


async def test_stream_creates_conversation_and_persists(client, fake_chat):
    fake_chat()
    sid = {"X-Session-Id": "conv-test-0001"}
    events = await _stream(client, {"question": QUESTION}, headers=sid)
    done = events[-1]
    assert done["event"] == "done"
    conv_id = done["conversation_id"]
    assert isinstance(conv_id, int)

    resp = await client.get("/api/v1/conversations", headers=sid)
    assert resp.status_code == 200
    convs = resp.json()
    assert len(convs) == 1
    assert convs[0]["id"] == conv_id
    assert convs[0]["title"] == QUESTION[:80]
    assert convs[0]["message_count"] == 2

    detail = (await client.get(f"/api/v1/conversations/{conv_id}", headers=sid)).json()
    roles = [m["role"] for m in detail["messages"]]
    assert roles == ["user", "assistant"]
    assert detail["messages"][0]["content"] == QUESTION
    assistant = detail["messages"][1]
    assert assistant["content"] == "Grounded answer [1]."
    assert assistant["category"] == "educational"
    assert any(s["reference"] == "2:255" for s in assistant["sources"])


async def test_follow_up_threads_history_through_condense(client, fake_chat):
    fake = fake_chat()
    sid = {"X-Session-Id": "conv-test-0002"}
    first = await _stream(client, {"question": QUESTION}, headers=sid)
    conv_id = first[-1]["conversation_id"]
    fake.text_calls.clear()

    follow_up = "And what does that verse teach about His power?"
    second = await _stream(
        client, {"question": follow_up, "conversation_id": conv_id}, headers=sid
    )
    assert second[-1]["conversation_id"] == conv_id

    # Call 1 = condense (classifier model, rewrite system); call 2 = generation
    assert len(fake.text_calls) == 2
    condense = fake.text_calls[0]
    assert condense["model"] == fake.classifier_model
    assert condense["system"].startswith("You rewrite")
    assert follow_up in condense["user"]
    generation = fake.text_calls[1]
    assert "Earlier conversation" in generation["user"]
    assert QUESTION in generation["user"]  # prior user turn is in the transcript
    assert f"Question: {follow_up}" in generation["user"]  # original wording answered

    detail = (await client.get(f"/api/v1/conversations/{conv_id}", headers=sid)).json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"] * 2


async def test_conversation_ownership_enforced(client, fake_chat):
    fake_chat()
    owner = {"X-Session-Id": "conv-test-0003"}
    intruder = {"X-Session-Id": "conv-test-0004"}
    events = await _stream(client, {"question": QUESTION}, headers=owner)
    conv_id = events[-1]["conversation_id"]

    resp = await client.get(f"/api/v1/conversations/{conv_id}", headers=intruder)
    assert resp.status_code == 404
    resp = await client.post(
        "/api/v1/ask/stream",
        json={"question": QUESTION, "conversation_id": conv_id},
        headers=intruder,
    )
    assert resp.status_code == 404
    # And without any session at all, continuing a thread is impossible
    resp = await client.post(
        "/api/v1/ask/stream", json={"question": QUESTION, "conversation_id": conv_id}
    )
    assert resp.status_code == 404


async def test_no_session_streams_without_persisting(client, fake_chat):
    fake_chat()
    events = await _stream(client, {"question": QUESTION})
    done = events[-1]
    assert done["answer"] == "Grounded answer [1]."
    assert done["conversation_id"] is None


async def test_nonstream_ask_also_persists(client, fake_chat):
    fake_chat()
    sid = {"X-Session-Id": "conv-test-0005"}
    resp = await client.post("/api/v1/ask", json={"question": QUESTION}, headers=sid)
    assert resp.status_code == 200
    conv_id = resp.json()["conversation_id"]
    assert isinstance(conv_id, int)
    detail = (await client.get(f"/api/v1/conversations/{conv_id}", headers=sid)).json()
    assert len(detail["messages"]) == 2


async def test_crisis_turns_are_not_persisted(client, fake_chat):
    fake_chat(category="sensitive_crisis")
    sid = {"X-Session-Id": "conv-test-0006"}
    events = await _stream(client, {"question": "I can't go on anymore"}, headers=sid)
    assert events[-1]["conversation_id"] is None
    resp = await client.get("/api/v1/conversations", headers=sid)
    assert resp.json() == []


async def test_delete_conversation(client, fake_chat):
    fake_chat()
    sid = {"X-Session-Id": "conv-test-0007"}
    events = await _stream(client, {"question": QUESTION}, headers=sid)
    conv_id = events[-1]["conversation_id"]

    resp = await client.delete(f"/api/v1/conversations/{conv_id}", headers=sid)
    assert resp.status_code == 204
    assert (await client.get(f"/api/v1/conversations/{conv_id}", headers=sid)).status_code == 404
    assert (await client.get("/api/v1/conversations", headers=sid)).json() == []
