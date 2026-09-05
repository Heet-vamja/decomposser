"""HybridFlow (ICML 2026) — Explain-Analyze-Generate planner → dependency DAG.

Reproduces HybridFlow's decomposition front-end: an "Explain-Analyze-Generate" (EAG)
meta-prompt asks the planner for an XML plan; it is deterministically parsed into a
DAG G(Q) = (T, E) where each subtask carries a natural-language description, a set of
prerequisite indices, and a role label. The plan is validated for acyclicity and
reachability; on failure the planner is re-prompted with the error (bounded repair),
and if that still fails the tasks are executed as a sequential chain fallback.
n_max = 7 subtasks, matching the paper.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from ..graph import break_cycles, chain_edges, prune_edges_to_nodes
from ..llm import LLMError, LLMResponse
from ..schemas import DecompositionResult, Edge, SubQuery
from .base import BaseDecomposer, DecomposerContext, rule_system

N_MAX = 7
_ROLES = {"explain", "analyze", "analyse", "generate"}

_SYSTEM = (
    "You are HybridFlow's edge planner. You turn a query into a dependency-aware plan "
    "using the Explain-Analyze-Generate method and output it as XML only."
)
_PROMPT = """Plan how to answer the query using the Explain-Analyze-Generate method:
- Explain subtasks surface the key elements / facts the query depends on.
- Analyze subtasks break the problem down and work out intermediate results.
- Generate subtasks compose the final answer.

Output ONLY this XML (no prose, no code fence), at most {n_max} subtasks:

<plan>
  <subtask id="1" role="Explain" parents="">short imperative description</subtask>
  <subtask id="2" role="Analyze" parents="1">...</subtask>
  <subtask id="3" role="Generate" parents="1,2">...</subtask>
</plan>

Rules: ids are 1..N in order; `parents` is a comma-separated list of earlier ids (empty
for none); the dependency graph must be acyclic; independent subtasks share no parents so
they can run in parallel.

Query:
{query}
"""
_REPAIR = """That plan was invalid: {error}
Return a corrected <plan>...</plan> XML with the same rules (ids 1..N, acyclic, at most {n_max} subtasks). XML only.
"""


class HybridFlowDecomposer(BaseDecomposer):
    id = "hybridflow-eag"
    name = "HybridFlow (Explain-Analyze-Generate)"
    kind = "llm"
    output_shape = "dag"
    tier = "large"

    def run(self, query: str, ctx: DecomposerContext) -> DecompositionResult:
        tier = ctx.tier(self.tier)
        messages = [
            {"role": "system", "content": rule_system(_SYSTEM)},
            {"role": "user", "content": _PROMPT.format(query=query, n_max=N_MAX)},
        ]
        notes: list[str] = []
        last: LLMResponse | None = None

        for attempt in range(3):  # 1 initial + 2 repairs
            try:
                resp = ctx.pool.chat(model_or_tier=tier, messages=messages, temperature=0.2)
            except LLMError as exc:
                return self._error_result(str(exc))
            last = resp

            parsed = _parse_plan(resp.text)
            if parsed is None:
                error = "could not parse <plan> XML"
            else:
                subqueries, edges = parsed
                edges = prune_edges_to_nodes(subqueries, edges)  # drop refs to non-existent ids
                edges, removed = break_cycles(subqueries, edges)
                if removed:
                    error = "plan contained a dependency cycle"
                elif not _all_reachable_from_roots(subqueries, edges):
                    error = "some subtasks are unreachable from a root"
                else:
                    if attempt > 0:
                        notes.append(f"repaired after {attempt} retry(ies)")
                    return self._finish(subqueries, edges, resp, notes)

            if attempt < 2:
                messages.append({"role": "assistant", "content": resp.text})
                messages.append(
                    {"role": "user", "content": _REPAIR.format(error=error, n_max=N_MAX)}
                )

        # chain fallback
        notes.append("chain fallback (planner never produced a valid DAG)")
        descs = _recover_descriptions(last.text if last else "") or [query.strip()]
        subqueries = [SubQuery(id=f"s{i}", text=t, role="Analyze") for i, t in enumerate(descs, 1)]
        return self._finish(subqueries, chain_edges(subqueries), last, notes)

    def _finish(
        self,
        subqueries: list[SubQuery],
        edges: list[Edge],
        resp: LLMResponse | None,
        notes: list[str],
    ) -> DecompositionResult:
        for s in subqueries:
            if s.model_tier is None:
                s.model_tier = "large" if (s.role or "").lower() == "generate" else "small"
        res = self._result(
            subqueries=subqueries,
            edges=edges,
            raw_output=resp.text if resp else "",
            model=resp.model if resp else None,
            latency_ms=resp.latency_ms if resp else 0,
            tokens=resp.tokens if resp else None,
            notes=notes,
        )
        return res


def _parse_plan(text: str) -> tuple[list[SubQuery], list[Edge]] | None:
    m = re.search(r"<plan\b.*?</plan>", text, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    try:
        root = ET.fromstring(m.group(0))
    except ET.ParseError:
        return None

    subqueries: list[SubQuery] = []
    edges: list[Edge] = []
    seen_ids: set[str] = set()
    for el in root.findall("subtask")[:N_MAX]:
        sid = (el.get("id") or "").strip()
        if not sid or sid in seen_ids:
            continue
        seen_ids.add(sid)
        role = (el.get("role") or "").strip().title() or None
        if role and role.lower() not in _ROLES:
            role = None
        desc = " ".join((el.text or "").split()).strip()
        if not desc:
            continue
        node_id = f"s{sid}"
        subqueries.append(SubQuery(id=node_id, text=desc, role=role))
        for parent in re.findall(r"\d+", el.get("parents") or ""):
            edges.append(Edge(from_=f"s{parent}", to=node_id))
    if not subqueries:
        return None
    return subqueries, edges


def _all_reachable_from_roots(subqueries: list[SubQuery], edges: list[Edge]) -> bool:
    ids = {s.id for s in subqueries}
    has_parent = {e.to for e in edges}
    roots = [i for i in ids if i not in has_parent]
    if not roots:
        return False
    adj: dict[str, list[str]] = {i: [] for i in ids}
    for e in edges:
        if e.from_ in adj and e.to in ids:
            adj[e.from_].append(e.to)
    seen: set[str] = set()
    stack = list(roots)
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        stack.extend(adj.get(n, []))
    return seen == ids


def _recover_descriptions(text: str) -> list[str]:
    descs = re.findall(r"<subtask[^>]*>(.*?)</subtask>", text, re.IGNORECASE | re.DOTALL)
    out = [" ".join(d.split()).strip() for d in descs]
    return [d for d in out if d][:N_MAX]
