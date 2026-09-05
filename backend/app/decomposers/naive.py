"""Naive one-shot decomposition prompt, run on the small and large model tiers.

Included so the arena can show how much decomposition quality changes with model
scale alone, holding the prompt fixed.
"""
from __future__ import annotations

from ..llm import LLMError
from ..schemas import DecompositionResult
from .base import (
    BaseDecomposer,
    DecomposerContext,
    deps_to_edges,
    items_to_subqueries,
    parse_numbered_list,
    rule_system,
)

_SYSTEM = "You are a precise query planner. Reply with only the numbered list, nothing else."
_PROMPT = """Break the user's query into the minimal set of atomic sub-questions needed to answer it fully.

Rules:
- One self-contained sub-question per line, numbered "1.", "2.", ...
- Do not invent constraints that are not in the original query.
- If a sub-question needs the answer to earlier ones, append " (depends on: <numbers>)".
- If the query is already atomic, return it as a single item.

Query:
{query}
"""


class _NaiveBase(BaseDecomposer):
    kind = "llm"
    output_shape = "linear"

    def run(self, query: str, ctx: DecomposerContext) -> DecompositionResult:
        tier = ctx.tier(self.tier)
        try:
            resp = ctx.pool.chat(
                model_or_tier=tier,
                messages=[
                    {"role": "system", "content": rule_system(_SYSTEM)},
                    {"role": "user", "content": _PROMPT.format(query=query)},
                ],
                temperature=0.2,
            )
        except LLMError as exc:
            return self._error_result(str(exc))

        items = parse_numbered_list(resp.text)
        if not items:
            return self._error_result("model returned no parseable list")
        subqueries = items_to_subqueries(items)
        edges = deps_to_edges(items)
        return self._result(
            subqueries=subqueries,
            edges=edges,
            raw_output=resp.text,
            model=resp.model,
            latency_ms=resp.latency_ms,
            tokens=resp.tokens,
        )


class NaiveSmallDecomposer(_NaiveBase):
    id = "naive-small"
    name = "Naive prompt (small model)"
    tier = "small"


class NaiveLargeDecomposer(_NaiveBase):
    id = "naive-large"
    name = "Naive prompt (large model)"
    tier = "large"
