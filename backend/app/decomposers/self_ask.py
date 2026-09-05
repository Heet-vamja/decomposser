"""Self-Ask (Press et al., 2022) — follow-up question chain.

Self-Ask has the model repeatedly decide whether a follow-up question is needed and
ask it before composing a final answer. Since this arena does not answer sub-questions,
the model is asked to lay out the full chain of follow-up questions it would ask, in
order. The result is a linear (and inherently dynamic-length) chain.
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

_SYSTEM = (
    "You use the Self-Ask method: before answering a hard question you ask yourself a "
    "chain of simpler follow-up questions, each one usable only after the previous is answered."
)
_PROMPT = """For the query below, write out the ordered chain of follow-up questions you would
ask yourself under the Self-Ask method — do NOT answer them.

Format: numbered "1.", "2.", ... Each follow-up should be answerable once the earlier
follow-ups are answered. The final follow-up's answer should settle the original query.

Query:
{query}
"""


class SelfAskDecomposer(BaseDecomposer):
    id = "self-ask"
    name = "Self-Ask"
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
                temperature=0.3,
            )
        except LLMError as exc:
            return self._error_result(str(exc))

        items = parse_numbered_list(resp.text)
        if not items:
            return self._error_result("model returned no parseable follow-up questions")
        subqueries = items_to_subqueries(items)
        res = self._result(
            subqueries=subqueries,
            edges=chain_edges(subqueries),
            raw_output=resp.text,
            model=resp.model,
            latency_ms=resp.latency_ms,
            tokens=resp.tokens,
        )
        res.notes.append("chain length is model-decided (dynamic)")
        return res
