"""Thin async wrapper around the Anthropic SDK.

All Claude access goes through ClaudeChat so the rest of the app (and the tests, via a
fake subclass) never touch the SDK directly. Models per the project plan: Sonnet 5 for
grounded answers, Haiku 4.5 for classification.
"""

import json
import logging

from anthropic import APIStatusError, AsyncAnthropic

from app.ai.base import AIUnavailable
from app.config import get_settings

log = logging.getLogger(__name__)

ANSWER_MODEL = "claude-sonnet-5"
CLASSIFIER_MODEL = "claude-haiku-4-5"

# Backward-compatible alias; new code should catch AIUnavailable.
ClaudeUnavailable = AIUnavailable


class ClaudeChat:
    answer_model = ANSWER_MODEL
    classifier_model = CLASSIFIER_MODEL

    def __init__(self, api_key: str | None = None):
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.anthropic_api_key
        self._client: AsyncAnthropic | None = None

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _get_client(self) -> AsyncAnthropic:
        if not self.available:
            raise ClaudeUnavailable("ANTHROPIC_API_KEY is not set")
        if self._client is None:
            self._client = AsyncAnthropic(api_key=self.api_key)
        return self._client

    async def text(
        self,
        *,
        model: str,
        system: str,
        user: str,
        max_tokens: int = 4096,
        effort: str | None = None,
    ) -> str:
        """One-shot text completion. Sonnet 5 runs adaptive thinking by default;
        sampling params are intentionally not exposed (rejected by current models)."""
        kwargs: dict = {}
        if effort:
            kwargs["output_config"] = {"effort": effort}
        try:
            response = await self._get_client().messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                **kwargs,
            )
        except APIStatusError as exc:
            raise ClaudeUnavailable(f"Claude API error {exc.status_code}: {exc.message}") from exc
        if response.stop_reason == "refusal":
            raise ClaudeUnavailable("Claude declined to answer this request")
        return "".join(b.text for b in response.content if b.type == "text")

    async def structured(
        self,
        *,
        model: str,
        system: str,
        user: str,
        schema: dict,
        max_tokens: int = 1024,
    ) -> dict:
        """Completion constrained to a JSON schema via output_config.format."""
        try:
            response = await self._get_client().messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_config={"format": {"type": "json_schema", "schema": schema}},
            )
        except APIStatusError as exc:
            raise ClaudeUnavailable(f"Claude API error {exc.status_code}: {exc.message}") from exc
        if response.stop_reason == "refusal":
            raise ClaudeUnavailable("Claude declined to answer this request")
        text = next((b.text for b in response.content if b.type == "text"), "")
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ClaudeUnavailable(f"Claude returned non-JSON structured output: {text[:200]}") from exc
