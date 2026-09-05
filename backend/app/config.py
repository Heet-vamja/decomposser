"""Runtime configuration loaded from the environment / .env file."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Raw token string: comma- or newline-separated. HF_TOKEN is accepted as an alias.
    hf_tokens: str = ""
    hf_token: str = ""

    small_model: str = "meta-llama/Llama-3.1-8B-Instruct"
    large_model: str = "meta-llama/Llama-3.3-70B-Instruct"
    judge_model: str = ""

    llm_timeout_seconds: float = 60.0
    llm_max_tokens: int = 1200

    frontend_origin: str = "http://localhost:5173"

    @property
    def token_pool(self) -> list[str]:
        raw = f"{self.hf_tokens},{self.hf_token}"
        seen: set[str] = set()
        tokens: list[str] = []
        for chunk in raw.replace("\n", ",").split(","):
            tok = chunk.strip()
            if tok and tok not in seen:
                seen.add(tok)
                tokens.append(tok)
        return tokens

    @property
    def resolved_judge_model(self) -> str:
        return self.judge_model.strip() or self.large_model


@lru_cache
def get_settings() -> Settings:
    return Settings()
