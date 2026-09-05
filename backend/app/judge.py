"""Reference-free LLM-as-judge for a single decomposition.

There is no gold decomposition to compare against, so the judge scores the sub-queries
and their dependency edges against the *original query alone*, on five criteria:

  coverage                 every intent / constraint in the query is in some sub-query
  minimality               no overlap, no over-splitting
  faithfulness             no invented constraints or hallucinated sub-intents
  standalone_answerability each sub-query is self-contained given only its DAG parents
  dependency_correctness   parallel-vs-sequential edges are justified; none missing

Structural facts (counts, depth, width, acyclicity) are computed deterministically in
``graph.py`` and passed in as context — they are not themselves scored.
"""
from __future__ import annotations

import json

from .llm import LLMError, LLMPool
from .schemas import DecompositionResult, JudgeCriterion, JudgeResult

_CRITERIA = [
    "coverage",
    "minimality",
    "faithfulness",
    "standalone_answerability",
    "dependency_correctness",
]

_SYSTEM = (
    "You are a strict evaluator of query-decomposition quality. You return only JSON. "
    "You never reward verbosity; a single sub-query is correct when the original query is atomic."
)

_PROMPT = """Original query:
{query}

Proposed decomposition ({n} sub-queries, {edges} dependency edges; graph is {shape}):
{decomposition}

Score each criterion from 1 (bad) to 5 (excellent):
- coverage: is every intent and constraint in the original query represented by some sub-query?
- minimality: are the sub-queries non-overlapping and not over-split? Penalise redundancy and needless fragmentation.
- faithfulness: do the sub-queries stay grounded in the query's wording, inventing no entity, name, fact, number, date, constraint, or intent that is not explicitly in it? Score 1 if any sub-query introduces something fabricated.
- standalone_answerability: could each sub-query be answered given only the answers to the sub-queries it lists as prerequisites (edges shown as "A -> B" meaning B needs A)?
- dependency_correctness: are the sequential-vs-parallel edges right — no missing prerequisite edges, no spurious ones?

Return ONLY:
{{
  "coverage": {{"score": <1-5>, "rationale": "<=25 words"}},
  "minimality": {{"score": <1-5>, "rationale": "<=25 words"}},
  "faithfulness": {{"score": <1-5>, "rationale": "<=25 words"}},
  "standalone_answerability": {{"score": <1-5>, "rationale": "<=25 words"}},
  "dependency_correctness": {{"score": <1-5>, "rationale": "<=25 words"}},
  "summary": "<=30 words overall"
}}
"""


def render_decomposition(result: DecompositionResult) -> str:
    lines = [f"- {s.id}: {s.text}" + (f"  [role={s.role}]" if s.role else "") for s in result.subqueries]
    if result.edges:
        lines.append("edges:")
        lines.extend(f"  {e.from_} -> {e.to}" for e in result.edges)
    else:
        lines.append("edges: (none — all parallel)")
    return "\n".join(lines)


def judge_decomposition(
    pool: LLMPool, query: str, result: DecompositionResult, *, model: str
) -> JudgeResult:
    if result.error:
        return _blank("decomposer failed; nothing to judge")
    if not result.subqueries:
        return _blank("no sub-queries produced")

    shape = "a DAG" if (result.stats and result.stats.edge_count) else "flat/parallel"
    prompt = _PROMPT.format(
        query=query,
        n=len(result.subqueries),
        edges=len(result.edges),
        shape=shape,
        decomposition=render_decomposition(result),
    )
    try:
        resp = pool.chat(
            model_or_tier=model,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
    except LLMError as exc:
        return _blank(str(exc))

    data = _load_json(resp.text)
    if data is None:
        return _blank("judge returned unparseable JSON")

    try:
        crits = {c: _criterion(data[c]) for c in _CRITERIA}
    except (KeyError, TypeError, ValueError):
        return _blank("judge JSON missing criteria")

    overall = round(sum(c.score for c in crits.values()) / len(crits), 2)
    return JudgeResult(
        **crits,
        overall=overall,
        summary=str(data.get("summary", "")).strip()[:400],
    )


def _criterion(raw: dict) -> JudgeCriterion:
    score = int(round(float(raw["score"])))
    score = max(1, min(5, score))
    return JudgeCriterion(score=score, rationale=str(raw.get("rationale", "")).strip()[:300])


def _blank(msg: str) -> JudgeResult:
    z = JudgeCriterion(score=0, rationale="")
    return JudgeResult(
        coverage=z,
        minimality=z,
        faithfulness=z,
        standalone_answerability=z,
        dependency_correctness=z,
        overall=0.0,
        summary="",
        error=msg,
    )


def _load_json(text: str) -> dict | None:
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        t = t[t.find("{") :]
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        s, e = t.find("{"), t.rfind("}")
        if s == -1 or e == -1:
            return None
        try:
            return json.loads(t[s : e + 1])
        except json.JSONDecodeError:
            return None
