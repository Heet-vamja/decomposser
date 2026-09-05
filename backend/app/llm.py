"""Hugging Face Inference client with a rotating token pool.

Decomposers and the judge call :func:`chat` with a model *tier* ("small" / "large")
or an explicit model id. Tokens are used round-robin and rotated on HTTP 429/503 so a
single throttled key does not stall a comparison.
"""
from __future__ import annotations

import itertools
import threading
import time
from dataclasses import dataclass

from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError

from .config import get_settings


class LLMError(RuntimeError):
    """Raised when every token in the pool fails for a request."""


@dataclass
class LLMResponse:
    text: str
    model: str
    latency_ms: int
    tokens: int | None


_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class LLMPool:
    def __init__(self) -> None:
        settings = get_settings()
        self._tokens = settings.token_pool
        self._timeout = settings.llm_timeout_seconds
        self._max_tokens = settings.llm_max_tokens
        self._small = settings.small_model
        self._large = settings.large_model
        self._lock = threading.Lock()
        self._cursor = itertools.cycle(range(len(self._tokens))) if self._tokens else None
        self._clients: dict[int, InferenceClient] = {}

    @property
    def has_tokens(self) -> bool:
        return bool(self._tokens)

    def resolve_model(self, model_or_tier: str) -> str:
        if model_or_tier == "small":
            return self._small
        if model_or_tier == "large":
            return self._large
        return model_or_tier

    def _client(self, idx: int) -> InferenceClient:
        client = self._clients.get(idx)
        if client is None:
            # provider="auto" routes through the HF Inference Providers router
            # (router.huggingface.co); the legacy api-inference.huggingface.co is retired.
            client = InferenceClient(
                provider="auto", api_key=self._tokens[idx], timeout=self._timeout
            )
            self._clients[idx] = client
        return client

    def _next_index(self) -> int:
        with self._lock:
            return next(self._cursor)

    def chat(
        self,
        *,
        model_or_tier: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int | None = None,
        response_format: dict | None = None,
    ) -> LLMResponse:
        if not self._tokens:
            raise LLMError("No Hugging Face tokens configured (set HF_TOKENS in backend/.env).")

        model = self.resolve_model(model_or_tier)
        attempts = max(len(self._tokens), 3)
        start = time.perf_counter()
        last_err: Exception | None = None

        for attempt in range(attempts):
            idx = self._next_index()
            try:
                kwargs: dict = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens or self._max_tokens,
                }
                if response_format is not None:
                    kwargs["response_format"] = response_format
                completion = self._client(idx).chat_completion(**kwargs)
                text = (completion.choices[0].message.content or "").strip()
                if not text:
                    last_err = LLMError(f"{model}: empty completion")
                    if attempt < attempts - 1:
                        time.sleep(0.5)
                        continue
                    raise last_err
                usage = getattr(completion, "usage", None)
                tokens = getattr(usage, "total_tokens", None) if usage else None
                latency_ms = int((time.perf_counter() - start) * 1000)
                return LLMResponse(text=text, model=model, latency_ms=latency_ms, tokens=tokens)
            except HfHubHTTPError as exc:  # rotate on throttle / transient upstream errors
                last_err = exc
                status = getattr(getattr(exc, "response", None), "status_code", None)
                if status in _RETRYABLE_STATUS and attempt < attempts - 1:
                    time.sleep(min(2 ** attempt * 0.5, 4.0))
                    continue
                if status not in _RETRYABLE_STATUS:
                    raise LLMError(f"{model}: {exc}") from exc
            except Exception as exc:  # noqa: BLE001 - surface as a uniform error
                last_err = exc
                if attempt < attempts - 1:
                    time.sleep(min(2 ** attempt * 0.5, 4.0))
                    continue

        raise LLMError(f"{model}: all {attempts} attempts failed ({last_err})")


_pool: LLMPool | None = None
_pool_lock = threading.Lock()


def get_pool() -> LLMPool:
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = LLMPool()
    return _pool
