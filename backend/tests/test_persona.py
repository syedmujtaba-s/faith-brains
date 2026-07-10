"""Tests for the persona catalogue and the learner persona selection."""

import pytest

from app.content.learning_paths import PATHS_BY_KEY
from app.content.personas import PERSONAS

pytestmark = pytest.mark.integration

SID = {"X-Session-Id": "persona-test-0001"}


async def test_personas_list(client):
    resp = await client.get("/api/v1/personas")
    assert resp.status_code == 200
    items = resp.json()
    assert {p["key"] for p in items} == {"learner", "student", "educator", "new_muslim"}
    for p in items:
        assert p["label"] and p["tagline"]
        assert 4 <= len(p["suggested_questions"]) <= 5
        assert p["recommended_paths"]
        assert all(key in PATHS_BY_KEY for key in p["recommended_paths"])
        assert "prompt_hint" not in p  # server-side only, never exposed


async def test_persona_questions_are_valid_ask_payloads():
    # Every suggested question must be submittable to AskRequest verbatim
    for p in PERSONAS:
        for q in p["suggested_questions"]:
            assert 3 <= len(q) <= 2000


async def test_put_persona_roundtrip(client):
    resp = await client.put(
        "/api/v1/learner/persona", json={"persona": "new_muslim"}, headers=SID
    )
    assert resp.status_code == 200
    assert resp.json()["persona"] == "new_muslim"

    resp = await client.put(
        "/api/v1/learner/persona", json={"persona": "educator"}, headers=SID
    )
    assert resp.json()["persona"] == "educator"

    resp = await client.put("/api/v1/learner/persona", json={"persona": None}, headers=SID)
    assert resp.json()["persona"] is None


async def test_put_persona_requires_session(client):
    resp = await client.put("/api/v1/learner/persona", json={"persona": "learner"})
    assert resp.status_code == 400


async def test_put_persona_invalid_value(client):
    resp = await client.put(
        "/api/v1/learner/persona", json={"persona": "scholar"}, headers=SID
    )
    assert resp.status_code == 422
