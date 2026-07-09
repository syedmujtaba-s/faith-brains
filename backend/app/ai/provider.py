"""Chat-provider selection.

AI_PROVIDER=openai | anthropic | auto (default). Auto prefers OpenAI when its key is
present (per project decision: generation runs on the OpenAI key), else Anthropic.
"""

from app.ai.base import ChatProvider
from app.ai.claude import ClaudeChat
from app.ai.openai_chat import OpenAIChat
from app.config import get_settings


def get_chat_provider() -> ChatProvider:
    settings = get_settings()
    provider = settings.ai_provider.lower()
    if provider == "openai":
        return OpenAIChat()
    if provider == "anthropic":
        return ClaudeChat()
    # auto
    openai = OpenAIChat()
    if openai.available:
        return openai
    return ClaudeChat()
