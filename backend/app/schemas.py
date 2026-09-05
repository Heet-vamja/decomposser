"""Pydantic models shared across the API surface."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

ModelTier = Literal["none", "small", "large"]
OutputShape = Literal["dag", "linear", "flat", "adaptive"]
DecomposerKind = Literal["deterministic", "llm"]


class SubQuery(BaseModel):
    id: str
    text: str
    role: Optional[str] = None          # e.g. HybridFlow's Explain / Analyze / Generate
    model_tier: Optional[ModelTier] = None  # routing suggestion, when the method makes one


class Edge(BaseModel):
    """`to` depends on `from_` (from_ must resolve before to)."""

    from_: str = Field(alias="from")
    to: str

    model_config = {"populate_by_name": True}


class GraphStats(BaseModel):
    node_count: int
    edge_count: int
    is_dag: bool
    depth: int            # longest dependency chain (nodes); 1 when there are no edges
    max_width: int        # largest set of mutually independent subqueries (parallelism)
    roots: int            # nodes with no prerequisites
    leaves: int           # nodes nothing depends on
    decomposed: bool      # False when the method chose to keep the query whole


class JudgeCriterion(BaseModel):
    score: int            # 1..5
    rationale: str


class JudgeResult(BaseModel):
    coverage: JudgeCriterion
    minimality: JudgeCriterion
    faithfulness: JudgeCriterion
    standalone_answerability: JudgeCriterion
    dependency_correctness: JudgeCriterion
    overall: float
    summary: str
    error: Optional[str] = None


class DecompositionResult(BaseModel):
    decomposer_id: str
    subqueries: list[SubQuery]
    edges: list[Edge]
    stats: Optional[GraphStats] = None
    raw_output: str = ""
    model: Optional[str] = None
    latency_ms: int = 0
    tokens: Optional[int] = None
    notes: list[str] = Field(default_factory=list)  # e.g. "repaired cycle", "chain fallback"
    error: Optional[str] = None
    judge: Optional[JudgeResult] = None


class CompareRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    decomposer_ids: Optional[list[str]] = None
    tier_override: Optional[Literal["small", "large"]] = None
    judge: bool = True


class CompareResponse(BaseModel):
    query: str
    judge_model: Optional[str] = None
    results: list[DecompositionResult]


class DecomposerInfo(BaseModel):
    id: str
    name: str
    kind: DecomposerKind
    output_shape: OutputShape
    tier: ModelTier
    origin: str
    origin_url: str
    how_it_works: str
    example: Optional[str] = None
