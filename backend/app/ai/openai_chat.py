"""OpenAI chat provider (generation + classification via the official SDK)."""

import json
import logging

from openai import AsyncOpenAI, OpenAIError

from app.ai.base import AIUnavailable
from app.config import get_settings

log = logging.getLogger(__name__)


class OpenAIChat:
    def __init__(self, api_key: str | None = None):
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.openai_api_key
        self.answer_model = settings.openai_answer_model
        self.classifier_model = settings.openai_classifier_model
        self._client: AsyncOpenAI | None = None

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _get_client(self) -> AsyncOpenAI:
        if not self.available:
            raise AIUnavailable("OPENAI_API_KEY is not set")
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def _create(self, *, model: str, system: str, user: str, max_tokens: int, **kwargs):
        try:
            return await self._get_client().chat.completions.create(
                model=model,
                max_completion_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                **kwargs,
            )
        except OpenAIError as exc:
            raise AIUnavailable(f"OpenAI API error: {exc}") from exc

    @staticmethod
    def _message(response):
        choice = response.choices[0]
        message = choice.message
        if getattr(message, "refusal", None):
            raise AIUnavailable("OpenAI declined to answer this request")
        if not (message.content or "").strip() and choice.finish_reason == "length":
            raise AIUnavailable(
                "OpenAI ran out of completion tokens before producing output "
                "(reasoning consumed the budget) — raise max_tokens"
            )
        return message

    async def text(
        self,
        *,
        model: str,
        system: str,
        user: str,
        max_tokens: int = 4096,
        effort: str | None = None,
    ) -> str:
        kwargs: dict = {}
        # reasoning_effort applies to reasoning models (gpt-5 family / o-series)
        if effort in ("low", "medium", "high") and (
            model.startswith("gpt-5") or model.startswith("o")
        ):
            kwargs["reasoning_effort"] = effort
        response = await self._create(
            model=model, system=system, user=user, max_tokens=max_tokens, **kwargs
        )
        return self._message(response).content or ""

    async def structured(
        self,
        *,
        model: str,
        system: str,
        user: str,
        schema: dict,
        max_tokens: int = 1024,
    ) -> dict:
        kwargs: dict = {}
        if model.startswith("gpt-5"):
            # Reasoning models spend max_completion_tokens on hidden reasoning first;
            # classification needs none of it, but does need output headroom.
            kwargs["reasoning_effort"] = "minimal"
            max_tokens = max(max_tokens, 2000)
        response = await self._create(
            model=model,
            system=system,
            user=user,
            max_tokens=max_tokens,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "result", "schema": schema, "strict": True},
            },
            **kwargs,
        )
        content = self._message(response).content or ""
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise AIUnavailable(
                f"OpenAI returned non-JSON structured output: {content[:200]}"
            ) from exc
