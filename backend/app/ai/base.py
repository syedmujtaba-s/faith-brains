"""Provider-neutral chat interface. Guard + answer engine depend only on this."""

from typing import Protocol, runtime_checkable


class AIUnavailable(RuntimeError):
    """No API key configured, provider error, or safety refusal."""


@runtime_checkable
class ChatProvider(Protocol):
    answer_model: str
    classifier_model: str

    @property
    def available(self) -> bool: ...

    async def text(
        self,
        *,
        model: str,
        system: str,
        user: str,
        max_tokens: int = 4096,
        effort: str | None = None,
    ) -> str: ...

    async def structured(
        self,
        *,
        model: str,
        system: str,
        user: str,
        schema: dict,
        max_tokens: int = 1024,
    ) -> dict: ...
