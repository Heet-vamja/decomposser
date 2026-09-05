from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.llm import LLMResponse  # noqa: E402


class FakePool:
    """Stand-in for LLMPool that replays canned responses."""

    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self.calls: list[dict] = []
        self.has_tokens = True

    def resolve_model(self, model_or_tier: str) -> str:
        return {"small": "fake-small", "large": "fake-large"}.get(model_or_tier, model_or_tier)

    def chat(self, *, model_or_tier: str, messages, **kwargs) -> LLMResponse:
        self.calls.append({"model_or_tier": model_or_tier, "messages": messages, **kwargs})
        text = self._responses.pop(0) if self._responses else ""
        return LLMResponse(
            text=text, model=self.resolve_model(model_or_tier), latency_ms=1, tokens=42
        )


@pytest.fixture
def fake_pool():
    return FakePool
