"""Milestone 4: admin auth, ask logging, rate limiting, security headers."""

import pytest

from app.ai.answer import AnswerService
from app.ai.claude import ClaudeChat
from app.api import routes
from app.api.ratelimit import search_limiter
from app.config import get_settings

pytestmark = pytest.mark.integration

TOKEN = "test-admin-token"


class FakeChat(ClaudeChat):
    def __init__(self):
        super().__init__(api_key="fake-key")

    async def structured(self, **kwargs) -> dict:
        return {"category": "educational", "reason": "test"}

    async def text(self, **kwargs) -> str:
        return "Logged answer [1]."


@pytest.fixture()
def admin_token(monkeypatch):
    monkeypatch.setattr(get_settings(), "admin_token", TOKEN)
    return TOKEN


async def test_admin_requires_token(client, admin_token):
    assert (await client.get("/api/v1/admin/stats")).status_code == 401
    assert (
        await client.get("/api/v1/admin/stats", headers={"X-Admin-Token": "wrong"})
    ).status_code == 401
    resp = await client.get("/api/v1/admin/stats", headers={"X-Admin-Token": TOKEN})
    assert resp.status_code == 200
    body = resp.json()
    assert body["verses"] == 4 and body["hadiths"] == 1


async def test_admin_disabled_with_default_token(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "admin_token", "change-me")
    resp = await client.get("/api/v1/admin/stats", headers={"X-Admin-Token": "change-me"})
    assert resp.status_code == 403


async def test_ask_is_logged_and_visible_in_admin(client, admin_token, monkeypatch):
    monkeypatch.setattr(
        routes, "answer_service", AnswerService(chat=FakeChat(), search=routes.search_service)
    )
    resp = await client.post(
        "/api/v1/ask", json={"question": "What does the Quran say about drowsiness and sleep?"}
    )
    assert resp.status_code == 200

    logs = await client.get("/api/v1/admin/asks", headers={"X-Admin-Token": TOKEN})
    assert logs.status_code == 200
    body = logs.json()
    assert body["total"] >= 1
    latest = body["items"][0]
    assert "drowsiness" in latest["question"]
    assert latest["category"] == "educational"
    assert latest["status"] == "ok"
    assert latest["latency_ms"] is not None


async def test_search_rate_limit(client, monkeypatch):
    monkeypatch.setattr(search_limiter, "limit", 3)
    search_limiter.reset()
    for _ in range(3):
        assert (await client.get("/api/v1/search?q=patience")).status_code == 200
    resp = await client.get("/api/v1/search?q=patience")
    assert resp.status_code == 429
    assert "retry-after" in {k.lower() for k in resp.headers.keys()}


async def test_security_headers(client):
    resp = await client.get("/api/v1/health")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
