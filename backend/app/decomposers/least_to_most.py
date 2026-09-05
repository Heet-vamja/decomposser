"""Least-to-Most prompting (Zhou et al., 2022) — decomposition stage only.

Least-to-Most first decomposes a problem into an ordered list of easier sub-problems,
then solves them sequentially so each answer feeds the next. This arena runs only the
decomposition stage, yielding a strict linear chain.
"""
from __future__ import annotations

from ..graph import chain_edges
from ..llm import LLMError
from ..schemas import DecompositionResult
from .base import (
    BaseDecomposer,
    DecomposerContext,
    items_to_subqueries,
    parse_numbered_list,
    rule_system,
)

_SYSTEM = "You decompose problems into an ordered list of simpler sub-problems. Output only the list."
_PROMPT = """To answer the query below, we need to solve a sequence of simpler sub-problems,
each building on the answers to the ones before it.

List those sub-problems in solving order, numbered "1.", "2.", ...
The last item should, once solved, yield the answer to the original query.

Query:
{query}
"""


class LeastToMostDecomposer(BaseDecomposer):
    id = "least-to-most"
    name = "Least-to-Most prompting"
    kind = "llm"
    output_shape = "linear"
    tier = "large"

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
        return self._result(
            subqueries=subqueries,
            edges=chain_edges(subqueries),
            raw_output=resp.text,
            model=resp.model,
            latency_ms=resp.latency_ms,
            tokens=resp.tokens,
        )
