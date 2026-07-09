from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # .env lives at the repo root; a backend-local .env (if any) wins
        env_file=(REPO_DIR / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://faithbrains:faithbrains@localhost:5433/faithbrains"

    voyage_api_key: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    # openai | anthropic | auto (auto prefers OpenAI when its key is set)
    ai_provider: str = "auto"
    openai_answer_model: str = "gpt-5-mini"
    openai_classifier_model: str = "gpt-5-nano"
    admin_token: str = "change-me"

    embedding_model: str = "voyage-4"
    embedding_dim: int = 1024
    gemini_api_key: str = ""
    gemini_embedding_model: str = "gemini-embedding-2"
    # voyage | gemini | auto (auto prefers Gemini when its key is set)
    embedding_provider: str = "auto"

    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
