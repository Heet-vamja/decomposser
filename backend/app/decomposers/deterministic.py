"""Rule-based decomposer — no LLM.

Splits the query into clauses on sentence boundaries and clause-level coordinating
conjunctions, then adds a sequential dependency edge whenever a clause refers back to
an earlier one through an anaphor ("it", "that", "the result", ...).
"""
from __future__ import annotations

import re
import time
from functools import lru_cache

from ..schemas import DecompositionResult, Edge, SubQuery
from .base import BaseDecomposer, DecomposerContext

_SPLIT_RE = re.compile(
    r"\s*(?:;|\band then\b|\bthen\b|\bafter that\b|\bafterwards\b|\bnext\b|\bfinally\b|"
    r"\bas well as\b|\balong with\b|\band also\b|,?\s+and\b|,)\s*",
    re.IGNORECASE,
)
_ANAPHORA = re.compile(
    r"\b(it|its|it's|that|this|these|those|they|them|their|the result|the former|"
    r"the latter|the above|the previous|such|the same)\b",
    re.IGNORECASE,
)
_HAS_VERB = re.compile(
    r"\b(is|are|was|were|be|been|being|has|have|had|do|does|did|"
    r"[a-z]+ing|[a-z]+ed|[a-z]+s|find|list|name|compare|explain|calculate|compute|"
    r"identify|determine|describe|give|show|tell|what|which|who|when|where|why|how)\b",
    re.IGNORECASE,
)


@lru_cache
def _nlp():
    try:
        import spacy

        try:
            return spacy.load("en_core_web_sm", disable=["ner", "lemmatizer"])
        except OSError:
            nlp = spacy.blank("en")
            nlp.add_pipe("sentencizer")
            return nlp
    except Exception:  # spacy missing entirely
        return None


def _sentences(text: str) -> list[str]:
    nlp = _nlp()
    if nlp is not None:
        return [s.text.strip() for s in nlp(text).sents if s.text.strip()]
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _clauses(sentence: str) -> list[str]:
    parts = [p.strip(" ,.;") for p in _SPLIT_RE.split(sentence)]
    parts = [p for p in parts if p and _HAS_VERB.search(p)]
    return parts or ([sentence.strip()] if sentence.strip() else [])


class DeterministicDecomposer(BaseDecomposer):
    id = "deterministic"
    name = "Rule-based splitter"
    kind = "deterministic"
    output_shape = "flat"
    tier = "none"

    def run(self, query: str, ctx: DecomposerContext) -> DecompositionResult:
        start = time.perf_counter()
        fragments: list[str] = []
        for sent in _sentences(query):
            fragments.extend(_clauses(sent))
        if not fragments:
            fragments = [query.strip()]

        question_like = query.strip().endswith("?") or bool(
            re.match(r"\s*(what|which|who|whom|whose|when|where|why|how|is|are|do|does|did|can|could|should|would)\b",
                     query, re.IGNORECASE)
        )

        subqueries: list[SubQuery] = []
        for i, frag in enumerate(fragments, start=1):
            text = frag[0].upper() + frag[1:] if frag else frag
            if question_like and not text.endswith(("?", ".")):
                text += "?"
            subqueries.append(SubQuery(id=f"s{i}", text=text))

        edges: list[Edge] = []
        for i in range(1, len(subqueries)):
            if _ANAPHORA.search(fragments[i]):
                edges.append(Edge(from_=f"s{i}", to=f"s{i + 1}"))

        latency_ms = int((time.perf_counter() - start) * 1000)
        res = self._result(
            subqueries=subqueries,
            edges=edges,
            raw_output="\n".join(f"{i}. {s.text}" for i, s in enumerate(subqueries, 1)),
            model=None,
            latency_ms=latency_ms,
        )
        if _nlp() is None:
            res.notes.append("spaCy unavailable — used regex sentence splitting")
        return res
