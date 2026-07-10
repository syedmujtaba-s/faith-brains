"""Embedding providers (Voyage, Gemini) behind one thin interface.

Vectors from different models are incompatible — embed.py wipes and re-embeds rows
whose stored embedding_model differs from the active embedder's model.
"""

import asyncio
import logging
from typing import Protocol

import httpx

from app.config import get_settings

log = logging.getLogger(__name__)

_API_URL = "https://api.voyageai.com/v1/embeddings"
_MAX_RETRIES = 9
_MAX_WAIT = 65.0  # free-tier accounts are limited to 3 RPM; ride it out, don't die
_FREE_TIER_SPACING = 21.0


class EmbeddingsUnavailable(RuntimeError):
    """Raised when no API key is configured or the provider keeps failing."""


class Embedder(Protocol):
    model: str
    dim: int

    @property
    def available(self) -> bool: ...

    async def embed(self, texts: list[str], input_type: str) -> list[list[float]]: ...

    async def embed_query(self, text: str) -> list[float]: ...


class VoyageEmbedder:
    def __init__(self, api_key: str | None = None, model: str | None = None, dim: int | None = None):
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.voyage_api_key
        self.model = model or settings.embedding_model
        self.dim = dim or settings.embedding_dim
        # Set after the first 429: minimum spacing between requests (adaptive throttle)
        self._min_interval = 0.0
        self._last_request = 0.0

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    async def embed(
        self,
        texts: list[str],
        input_type: str,
        *,
        attempts: int = _MAX_RETRIES,
        max_wait: float = _MAX_WAIT,
        throttle: bool = True,
        timeout_s: float = 120.0,
    ) -> list[list[float]]:
        """input_type: 'document' for corpus rows, 'query' for search queries.

        Defaults suit the bulk crawl (patient, throttled). Query-time callers pass
        a small budget instead — see embed_query."""
        if not self.available:
            raise EmbeddingsUnavailable("VOYAGE_API_KEY is not set")
        payload = {
            "input": texts,
            "model": self.model,
            "input_type": input_type,
            "output_dimension": self.dim,
        }
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            for attempt in range(attempts):
                if throttle and self._min_interval:
                    since = asyncio.get_event_loop().time() - self._last_request
                    if since < self._min_interval:
                        await asyncio.sleep(self._min_interval - since)
                self._last_request = asyncio.get_event_loop().time()
                try:
                    resp = await client.post(
                        _API_URL,
                        json=payload,
                        headers={"Authorization": f"Bearer {self.api_key}"},
                    )
                except httpx.HTTPError as exc:  # DNS blips, timeouts, resets — retryable
                    if attempt < attempts - 1:
                        wait = min(2.0**attempt, max_wait)
                        log.warning("Voyage network error (%s), retrying in %.0fs", exc, wait)
                        await asyncio.sleep(wait)
                        continue
                    raise EmbeddingsUnavailable(f"Voyage network error: {exc}") from exc
                if resp.status_code == 200:
                    data = resp.json()["data"]
                    return [row["embedding"] for row in data]
                if resp.status_code == 429 and throttle and not self._min_interval:
                    self._min_interval = _FREE_TIER_SPACING
                    log.warning("Voyage rate limit hit — throttling to one request/%.0fs", self._min_interval)
                if resp.status_code in (429, 500, 502, 503, 529) and attempt < attempts - 1:
                    wait = min(float(resp.headers.get("retry-after") or 2**attempt), max_wait)
                    log.warning("Voyage %s, retrying in %.0fs", resp.status_code, wait)
                    await asyncio.sleep(wait)
                    continue
                raise EmbeddingsUnavailable(
                    f"Voyage API error {resp.status_code}: {resp.text[:300]}"
                )
        raise EmbeddingsUnavailable("Voyage API: retries exhausted")

    async def embed_query(self, text: str) -> list[float]:
        # Live searches must never hang behind the crawl's shared 3 RPM budget:
        # two quick tries, then EmbeddingsUnavailable — the caller degrades to
        # lexical-only search instead of stalling the answer.
        vectors = await self.embed(
            [text], input_type="query", attempts=2, max_wait=2.0, throttle=False, timeout_s=8.0
        )
        return vectors[0]


class GeminiEmbedder:
    """gemini-embedding-2 via the google-genai SDK (sync client run in a thread).

    Per the Gemini docs: task instructions go in the text itself (no task_type param),
    each input is wrapped in a Content object to get separate embeddings, and truncated
    output_dimensionality (our 1024) is auto-normalized by the model.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None, dim: int | None = None):
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.gemini_api_key
        self.model = model or settings.gemini_embedding_model
        self.dim = dim or settings.embedding_dim
        self._client = None

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _get_client(self):
        if not self.available:
            raise EmbeddingsUnavailable("GEMINI_API_KEY is not set")
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def format_text(self, text: str, input_type: str) -> str:
        if input_type == "query":
            return f"task: search result | query: {text}"
        return f"title: none | text: {text}"

    async def embed(self, texts: list[str], input_type: str) -> list[list[float]]:
        from google.genai import errors, types

        client = self._get_client()
        contents = [
            types.Content(parts=[types.Part.from_text(text=self.format_text(t, input_type))])
            for t in texts
        ]
        config = types.EmbedContentConfig(output_dimensionality=self.dim)
        for attempt in range(_MAX_RETRIES):
            try:
                result = await asyncio.to_thread(
                    client.models.embed_content,
                    model=self.model,
                    contents=contents,
                    config=config,
                )
                vectors = [list(e.values) for e in result.embeddings]
                if len(vectors) != len(texts):
                    raise EmbeddingsUnavailable(
                        f"Gemini returned {len(vectors)} embeddings for {len(texts)} inputs "
                        "(aggregation? inputs must each be a Content object)"
                    )
                return vectors
            except errors.APIError as exc:
                code = getattr(exc, "code", None)
                if code == 429 and "PerDay" in str(exc):
                    # Daily quota (free tier: 1000 embed requests/day, each text counts)
                    # won't reset within any retry window — fail fast with the real story.
                    raise EmbeddingsUnavailable(
                        "Gemini free-tier DAILY embedding quota exhausted (1000/day; "
                        "resets midnight Pacific). Use EMBEDDING_PROVIDER=voyage or add "
                        "billing to the Google project."
                    ) from exc
                if code in (429, 500, 502, 503) and attempt < _MAX_RETRIES - 1:
                    wait = min(2.0**attempt, _MAX_WAIT)
                    log.warning("Gemini %s, retrying in %.0fs", code, wait)
                    await asyncio.sleep(wait)
                    continue
                raise EmbeddingsUnavailable(f"Gemini API error {code}: {exc}") from exc
        raise EmbeddingsUnavailable("Gemini API: retries exhausted")

    async def embed_query(self, text: str) -> list[float]:
        return (await self.embed([text], input_type="query"))[0]


def get_embedder() -> Embedder:
    """EMBEDDING_PROVIDER=voyage | gemini | auto (auto prefers Gemini when its key is set)."""
    settings = get_settings()
    provider = settings.embedding_provider.lower()
    if provider == "gemini":
        return GeminiEmbedder()
    if provider == "voyage":
        return VoyageEmbedder()
    gemini = GeminiEmbedder()
    return gemini if gemini.available else VoyageEmbedder()
