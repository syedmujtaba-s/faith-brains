"""In-memory sliding-window rate limiting, keyed by client IP.

Good for a single-process deployment; swap the store for Redis when scaling out.
"""

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: float = 60.0):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def reset(self) -> None:
        self._hits.clear()

    def check(self, key: str) -> None:
        now = time.monotonic()
        hits = self._hits[key]
        while hits and hits[0] <= now - self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            retry_after = max(1, int(hits[0] + self.window - now) + 1)
            raise HTTPException(
                429,
                "Too many requests — please slow down.",
                headers={"Retry-After": str(retry_after)},
            )
        hits.append(now)


ask_limiter = SlidingWindowLimiter(limit=15)  # AI generation is the expensive path
search_limiter = SlidingWindowLimiter(limit=60)


def _client_key(request: Request) -> str:
    # Behind a proxy, trust the first X-Forwarded-For hop; else the socket peer.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def limit_ask(request: Request) -> None:
    ask_limiter.check(_client_key(request))


async def limit_search(request: Request) -> None:
    search_limiter.check(_client_key(request))
