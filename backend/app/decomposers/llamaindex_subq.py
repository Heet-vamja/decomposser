"""LlamaIndex-style SubQuestionQueryEngine question generation.

Reproduces the shape of LlamaIndex's question generator: a single LLM call that emits
a JSON list of sub-questions over the "data sources", with no dependency structure —
every sub-question is assumed independently answerable and run in parallel.
The tool/data-source machinery is dropped since this arena has no retrieval corpus.
"""
from __future__ import annotations

import json

from ..llm import LLMError
from ..schemas import DecompositionResult, SubQuery
from .base import BaseDecomposer, DecomposerContext, rule_system, strip_code_fences

_SYSTEM = (
    "You are a world-class state-of-the-art agent. You break a complex question into "
    "simpler sub-questions that can each be answered independently."
)
_PROMPT = """Given a user question, output a JSON object with a single key "items" whose value
is a list of sub-questions. Each item is an object: {{"sub_question": "<text>"}}.
The sub-questions must together cover the original question and each must be answerable on its own.

Return only JSON.

Question: {query}
"""


class LlamaIndexSubQuestionDecomposer(BaseDecomposer):
    id = "llamaindex-subq"
    name = "LlamaIndex SubQuestionQueryEngine"
    kind = "llm"
    output_shape = "flat"
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
                temperature=0.1,
                response_format={"type": "json_object"},
            )
        except LLMError as exc:
            return self._error_result(str(exc))

        items = _extract_items(resp.text)
        if not items:
            return self._error_result("model returned no parseable sub-questions")

        subqueries = [
            SubQuery(id=f"s{i}", text=str(q).strip())
            for i, q in enumerate(items, start=1)
            if str(q).strip()
        ]
        return self._result(
            subqueries=subqueries,
            edges=[],  # flat by construction
            raw_output=resp.text,
            model=resp.model,
            latency_ms=resp.latency_ms,
            tokens=resp.tokens,
        )


def _extract_items(text: str) -> list[str]:
    raw = strip_code_fences(text)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end == -1:
            return []
        try:
            data = json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            return []
    items = data.get("items", data) if isinstance(data, dict) else data
    out: list[str] = []
    for it in items or []:
        if isinstance(it, dict):
            out.append(it.get("sub_question") or it.get("question") or "")
        else:
            out.append(str(it))
    return [o for o in out if o]
