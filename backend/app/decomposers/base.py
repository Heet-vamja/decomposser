"""Base class, shared parsing helpers and the decomposer registry."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import ClassVar

from ..graph import break_cycles, compute_stats, prune_edges_to_nodes
from ..llm import LLMPool
from ..schemas import DecompositionResult, Edge, GraphStats, SubQuery

REGISTRY: dict[str, "BaseDecomposer"] = {}

# Appended to every LLM decomposer's system message so no method is free to
# introduce entities, facts or constraints that are not in the user's query.
NO_INVENTION = (
    "Ground every sub-query strictly in the wording of the original query. Do not add, "
    "assume, infer, or invent any entity, name, fact, number, date, or constraint that "
    "is not explicitly stated in it. If the query is vague, keep the sub-query vague."
)


def rule_system(system: str) -> str:
    """Combine a decomposer's system prompt with the shared no-invention rule."""
    return f"{system}\n\n{NO_INVENTION}"


@dataclass
class DecomposerContext:
    pool: LLMPool
    tier_override: str | None = None  # "small" | "large" | None
    notes: list[str] = field(default_factory=list)

    def tier(self, default: str) -> str:
        if default == "none":
            return "none"
        return self.tier_override or default


class BaseDecomposer:
    id: ClassVar[str]
    name: ClassVar[str]
    kind: ClassVar[str]            # "deterministic" | "llm"
    output_shape: ClassVar[str]   # "dag" | "linear" | "flat" | "adaptive"
    tier: ClassVar[str] = "large"  # default model tier for llm decomposers

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if getattr(cls, "id", None):
            REGISTRY[cls.id] = cls()

    # subclasses implement this
    def run(self, query: str, ctx: DecomposerContext) -> DecompositionResult:  # pragma: no cover
        raise NotImplementedError

    # ---- helpers -------------------------------------------------------------

    def _result(
        self,
        *,
        subqueries: list[SubQuery],
        edges: list[Edge],
        raw_output: str = "",
        model: str | None = None,
        latency_ms: int = 0,
        tokens: int | None = None,
        notes: list[str] | None = None,
        decomposed: bool | None = None,
    ) -> DecompositionResult:
        notes = list(notes or [])
        edges = prune_edges_to_nodes(subqueries, edges)
        edges, broke_cycle = break_cycles(subqueries, edges)
        if broke_cycle:
            notes.append("dropped edge(s) to keep the dependency graph acyclic")
        if decomposed is None:
            decomposed = len(subqueries) > 1
        stats: GraphStats = compute_stats(subqueries, edges, decomposed=decomposed)
        return DecompositionResult(
            decomposer_id=self.id,
            subqueries=subqueries,
            edges=edges,
            stats=stats,
            raw_output=raw_output,
            model=model,
            latency_ms=latency_ms,
            tokens=tokens,
            notes=notes,
        )

    def _error_result(self, message: str) -> DecompositionResult:
        return DecompositionResult(
            decomposer_id=self.id,
            subqueries=[],
            edges=[],
            stats=compute_stats([], [], decomposed=False),
            error=message,
        )


# ---- shared text parsing ---------------------------------------------------

_NUM_LINE = re.compile(r"^\s*(?:\(?(\d+)\)?[.):\]]|[-*•‣▪])\s+(.*\S)\s*$")
_DEP_TOKEN = re.compile(
    r"\(?\s*(?:depends?\s*on|deps?|after|requires?|needs?)\s*[:=]?\s*([0-9,\sand&#]+)\)?",
    re.IGNORECASE,
)
_ID_RE = re.compile(r"\d+")


@dataclass
class ParsedItem:
    index: int          # 1-based position
    text: str
    deps: list[int]     # 1-based indices this item depends on


def parse_numbered_list(text: str) -> list[ParsedItem]:
    """Parse a numbered / bulleted list, extracting inline `depends on: N` hints."""
    items: list[ParsedItem] = []
    for raw_line in text.splitlines():
        line = raw_line.replace("**", "").replace("__", "").rstrip()
        m = _NUM_LINE.match(line)
        if not m:
            continue
        body = m.group(2).strip(" *_`")
        deps: list[int] = []
        dep_match = _DEP_TOKEN.search(body)
        if dep_match:
            deps = [int(x) for x in _ID_RE.findall(dep_match.group(1))]
            body = _DEP_TOKEN.sub("", body).strip(" .;,-—")
        if not body:
            continue
        idx = int(m.group(1)) if m.group(1) else len(items) + 1
        items.append(ParsedItem(index=idx, text=body, deps=deps))
    # normalise to contiguous, unique indices 1..n in encounter order, remapping deps
    order: dict[int, int] = {}
    for pos, it in enumerate(items):
        order.setdefault(it.index, pos + 1)
    for pos, it in enumerate(items):
        new_index = pos + 1
        it.deps = sorted({order[d] for d in it.deps if d in order and order[d] != new_index})
        it.index = new_index
    return items


def items_to_subqueries(items: list[ParsedItem], prefix: str = "s") -> list[SubQuery]:
    return [SubQuery(id=f"{prefix}{it.index}", text=it.text) for it in items if it.text]


def deps_to_edges(items: list[ParsedItem], prefix: str = "s") -> list[Edge]:
    edges: list[Edge] = []
    for it in items:
        for d in it.deps:
            edges.append(Edge(from_=f"{prefix}{d}", to=f"{prefix}{it.index}"))
    return edges


def strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z0-9_-]*\n", "", t)
        t = re.sub(r"\n```\s*$", "", t)
    return t.strip()
