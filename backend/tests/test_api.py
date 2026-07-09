"""Integration tests — need Postgres from docker compose (skipped if unreachable)."""

import pytest

pytestmark = pytest.mark.integration


async def test_health(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["verses"] == 4
    assert body["hadiths"] == 1


async def test_editions(client):
    resp = await client.get("/api/v1/editions")
    assert resp.status_code == 200
    keys = [e["key"] for e in resp.json()]
    assert "english_saheeh" in keys


async def test_surah_listing_and_detail(client):
    resp = await client.get("/api/v1/quran/surahs")
    assert resp.status_code == 200
    assert len(resp.json()) == 3

    resp = await client.get("/api/v1/quran/2")
    assert resp.status_code == 200
    body = resp.json()
    assert body["surah"]["name_transliterated"] == "Al-Baqara"
    assert [v["ayah"] for v in body["verses"]] == [153, 255]


async def test_verse_detail_with_translation(client):
    resp = await client.get("/api/v1/quran/2/255")
    assert resp.status_code == 200
    body = resp.json()
    assert "Ever-Living" in body["translations"][0]["text"]
    assert resp.json()["reference"] == "2:255"


async def test_verse_404(client):
    resp = await client.get("/api/v1/quran/2/999")
    assert resp.status_code == 404


async def test_hadith_listing_paginated(client):
    resp = await client.get("/api/v1/hadith/bukhari?offset=0&limit=10")
    assert resp.status_code == 200
    body = resp.json()
    assert body["collection_name"] == "Sahih al-Bukhari"
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["number"] == "1"

    resp = await client.get("/api/v1/hadith/nosuchcollection")
    assert resp.status_code == 404


async def test_hadith_detail_and_gradings(client):
    resp = await client.get("/api/v1/hadith/bukhari/1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["book_name"] == "Revelation"
    assert body["gradings"][0]["grade"] == "Sahih"


async def test_search_reference_shortcircuit(client):
    resp = await client.get("/api/v1/search", params={"q": "2:255"})
    body = resp.json()
    assert body["mode"] == "reference"
    assert body["results"][0]["reference"] == "2:255"
    assert body["results"][0]["translation"] is not None


async def test_search_surah_name_reference(client):
    resp = await client.get("/api/v1/search", params={"q": "baqara 255"})
    body = resp.json()
    assert body["mode"] == "reference"
    assert body["results"][0]["surah"] == 2


async def test_search_hadith_reference(client):
    resp = await client.get("/api/v1/search", params={"q": "bukhari 1"})
    body = resp.json()
    assert body["mode"] == "reference"
    assert body["results"][0]["type"] == "hadith"
    assert body["results"][0]["number"] == "1"


async def test_search_fulltext_english(client):
    resp = await client.get("/api/v1/search", params={"q": "drowsiness sleep"})
    body = resp.json()
    assert body["mode"] == "hybrid"
    assert "fulltext" in body["signals_used"]
    assert any(r["type"] == "quran" and r["reference"] == "2:255" for r in body["results"])


async def test_search_arabic_query(client):
    resp = await client.get("/api/v1/search", params={"q": "الحي القيوم"})
    body = resp.json()
    assert "arabic" in body["signals_used"]
    assert body["results"][0]["reference"] == "2:255"


async def test_search_hadith_fulltext(client):
    resp = await client.get(
        "/api/v1/search", params={"q": "reward of deeds intentions", "scope": "hadith"}
    )
    body = resp.json()
    assert any(r["type"] == "hadith" for r in body["results"])


async def test_search_scope_quran_excludes_hadith(client):
    resp = await client.get("/api/v1/search", params={"q": "intentions", "scope": "quran"})
    assert all(r["type"] == "quran" for r in resp.json()["results"])
