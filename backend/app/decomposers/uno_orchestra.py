"""Uno-Orchestra — parsimonious, adaptive decomposition.

Uno-Orchestra uses a single LLM call that jointly decides *whether* to decompose and,
if so, emits a small dependency graph where each subtask carries a (model, primitive)
routing pair; simple queries "collapse to a single direct-answer turn at zero dispatch
cost". This reproduction keeps the decision + dependency-graph output and the
small/large routing pair, and drops the primitive catalogue.
"""
from __future__ import annotations

import json

from ..llm import LLMError
from ..schemas import DecompositionResult, Edge, SubQuery
from .base import BaseDecomposer, DecomposerContext, rule_system, strip_code_fences

_SYSTEM = (
    "You are Uno-Orchestra, a parsimonious router. You decompose a query ONLY when it is "
    "genuinely compositional; otherwise you answer it in a single direct turn."
)
_PROMPT = """Decide whether the query needs decomposition.

Return ONLY JSON:
{{
  "decompose": true | false,
  "subtasks": [
    {{"id": 1, "text": "<subtask>", "deps": [], "model": "small" | "large"}}
  ]
}}

If "decompose" is false, return a single subtask that restates the query with "model"
set by its difficulty. If true, give 2-6 subtasks; "deps" lists the ids a subtask needs
first; independent subtasks have deps [] so they run in parallel; route cheap lookups to
"small" and hard reasoning/generation to "large".

Query:
{query}
"""


class UnoOrchestraDecomposer(BaseDecomposer):
    id = "uno-orchestra"
    name = "Uno-Orchestra (adaptive)"
    kind = "llm"
    output_shape = "adaptive"
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

        data = _load_json(resp.text)
        if data is None:
            return self._error_result("model returned no parseable JSON plan")

        raw_subtasks = data.get("subtasks") or []
        decompose = bool(data.get("decompose")) and len(raw_subtasks) > 1

        subqueries: list[SubQuery] = []
        id_map: dict[str, str] = {}
        for pos, st in enumerate(raw_subtasks, start=1):
            if not isinstance(st, dict):
                continue
            text = str(st.get("text", "")).strip()
            if not text:
                continue
            node_id = f"s{pos}"
            id_map[str(st.get("id", pos))] = node_id
            tier_val = st.get("model")
            subqueries.append(
                SubQuery(
                    id=node_id,
                    text=text,
                    model_tier=tier_val if tier_val in ("small", "large") else None,
                )
            )

        if not subqueries:
            subqueries = [SubQuery(id="s1", text=query.strip(), model_tier="large")]
            decompose = False

        edges: list[Edge] = []
        if decompose:
            for pos, st in enumerate(raw_subtasks, start=1):
                if not isinstance(st, dict):
                    continue
                target = f"s{pos}"
                for dep in st.get("deps", []) or []:
                    src = id_map.get(str(dep))
                    if src and src != target:
                        edges.append(Edge(from_=src, to=target))

        res = self._result(
            subqueries=subqueries,
            edges=edges,
            raw_output=resp.text,
            model=resp.model,
            latency_ms=resp.latency_ms,
            tokens=resp.tokens,
            decomposed=decompose,
        )
        res.notes.append("chose to decompose" if decompose else "chose NOT to decompose")
        return res


def _load_json(text: str) -> dict | None:
    raw = strip_code_fences(text)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end == -1:
            return None
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            return None
