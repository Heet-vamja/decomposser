"""Route-and-Reason (R2-Reasoner) Task Decomposer — inference-only reproduction.

R2-Reasoner's router has a Task Decomposer that "generates a structured sequence of
sub-tasks from a complex input", chain-ordered and solved sequentially, and a Subtask
Allocator that assigns each to a model. Here we reproduce the decomposer's prompt
(paper Appendix, generalised from the P3 template) and its Allocator's small/large
routing heuristic. No RL checkpoint is used — the base instruct model is prompted directly.
"""
from __future__ import annotations

import re

from ..graph import chain_edges
from ..llm import LLMError
from ..schemas import DecompositionResult, SubQuery
from .base import BaseDecomposer, DecomposerContext, rule_system

_SYSTEM = "You are a task decomposer. Output only the numbered step list."
_PROMPT = """You will be given a task. To better accomplish it, break the task into multiple
steps, preferably between 3 and 8 steps, organized in a chain-like manner so that the steps
are solved following a certain order (each step may use the results of the earlier ones).

Write each step on its own line as:
step 1: <what to work out>
step 2: <what to work out>
...

Task:
{query}
"""

_STEP_RE = re.compile(r"^\s*(?:step\s*)?(\d+)\s*[:.)\-]\s*(.+\S)\s*$", re.IGNORECASE)
# lightweight difficulty cues the R2 Subtask Allocator would learn to detect
_HARD_CUES = re.compile(
    r"\b(prove|derive|calculate|compute|optimi[sz]e|algorithm|integral|infer|"
    r"compare|trade-?off|synthesi[sz]e|design|multi-step|why|analy[sz]e)\b",
    re.IGNORECASE,
)


class R2ReasonerDecomposer(BaseDecomposer):
    id = "r2-reasoner"
    name = "Route-and-Reason Task Decomposer"
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

        steps: list[str] = []
        for raw_line in resp.text.splitlines():
            line = raw_line.replace("**", "").replace("__", "").strip()
            m = _STEP_RE.match(line)
            if m:
                steps.append(m.group(2).strip(" *_`"))
        if not steps:
            return self._error_result(
                f"model returned no parseable steps (raw: {resp.text[:200]!r})"
            )

        subqueries = [
            SubQuery(
                id=f"s{i}",
                text=t,
                model_tier="large" if _HARD_CUES.search(t) else "small",
            )
            for i, t in enumerate(steps, start=1)
        ]
        res = self._result(
            subqueries=subqueries,
            edges=chain_edges(subqueries),
            raw_output=resp.text,
            model=resp.model,
            latency_ms=resp.latency_ms,
            tokens=resp.tokens,
        )
        res.notes.append("model_tier per step = Subtask Allocator heuristic (small vs. large)")
        return res
