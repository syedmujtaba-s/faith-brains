"""Learner sessions (saved items, path progress) and the tafsir endpoint."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.models import QuranVerse, Tafsir

pytestmark = pytest.mark.integration

SID = {"X-Session-Id": "test-session-0001"}


async def test_saved_requires_session_header(client):
    assert (await client.get("/api/v1/saved")).status_code == 400
    resp = await client.get("/api/v1/saved", headers={"X-Session-Id": "x"})  # too short
    assert resp.status_code == 400


async def test_saved_roundtrip(client):
    resp = await client.post(
        "/api/v1/saved", json={"kind": "quran", "reference": "2:255"}, headers=SID
    )
    assert resp.status_code == 200
    assert {"kind": "quran", "reference": "2:255"} in resp.json()

    # duplicate save is idempotent
    resp = await client.post(
        "/api/v1/saved", json={"kind": "quran", "reference": "2:255"}, headers=SID
    )
    assert len([s for s in resp.json() if s["reference"] == "2:255"]) == 1

    resp = await client.delete("/api/v1/saved?kind=quran&reference=2:255", headers=SID)
    assert resp.json() == []


async def test_paths_list_detail_and_progress(client):
    paths = (await client.get("/api/v1/learn/paths")).json()
    keys = {p["key"] for p in paths}
    assert "salah-basics" in keys and all(p["completed_count"] == 0 for p in paths)

    detail = (await client.get("/api/v1/learn/paths/salah-basics", headers=SID)).json()
    step = next(s for s in detail["steps"] if s["key"] == "help-through-prayer")
    assert step["reference"] == "2:153"
    assert step["text"] and "patience" in step["text"].lower()  # hydrated from seeded corpus
    assert step["completed"] is False

    resp = await client.post(
        "/api/v1/learn/paths/salah-basics/steps/help-through-prayer/complete", headers=SID
    )
    assert resp.status_code == 200
    assert resp.json()["completed"] == ["help-through-prayer"]

    detail = (await client.get("/api/v1/learn/paths/salah-basics", headers=SID)).json()
    assert next(s for s in detail["steps"] if s["key"] == "help-through-prayer")["completed"]

    paths = (await client.get("/api/v1/learn/paths", headers=SID)).json()
    assert next(p for p in paths if p["key"] == "salah-basics")["completed_count"] == 1

    assert (
        await client.post("/api/v1/learn/paths/salah-basics/steps/nope/complete", headers=SID)
    ).status_code == 404


async def test_verse_tafsir_endpoint(client, test_engine):
    async with async_sessionmaker(test_engine, expire_on_commit=False)() as session:
        vid = (
            await session.execute(
                select(QuranVerse.id).where(
                    QuranVerse.surah_number == 2, QuranVerse.ayah_number == 255
                )
            )
        ).scalar_one()
        session.add(
            Tafsir(
                verse_id=vid,
                source_key="en-test-tafsir",
                source_name="Test Tafsir",
                language="english",
                text="This is the greatest verse of the Quran.",
            )
        )
        await session.commit()

    rows = (await client.get("/api/v1/quran/2/255/tafsir")).json()
    assert len(rows) == 1
    assert rows[0]["source_name"] == "Test Tafsir"
    assert (await client.get("/api/v1/quran/1/1/tafsir")).json() == []
