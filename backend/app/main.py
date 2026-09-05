"""FastAPI entrypoint for the Query Decomposer Arena."""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .decomposers import REGISTRY, DecomposerContext
from .judge import judge_decomposition
from .llm import get_pool
from .schemas import (
    CompareRequest,
    CompareResponse,
    DecomposerInfo,
    DecompositionResult,
)

DATA_DIR = Path(__file__).parent / "data"
_CATALOG = json.loads((DATA_DIR / "catalog.json").read_text())
_SAMPLES = json.loads((DATA_DIR / "sample_queries.json").read_text())

app = FastAPI(title="Query Decomposer Arena", version="1.0.0")
_ALLOWED_ORIGINS = [o.strip() for o in get_settings().frontend_origin.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _catalog() -> list[DecomposerInfo]:
    infos: list[DecomposerInfo] = []
    for dec_id, dec in REGISTRY.items():
        meta = _CATALOG.get(dec_id, {})
        infos.append(
            DecomposerInfo(
                id=dec_id,
                name=dec.name,
                kind=dec.kind,
                output_shape=dec.output_shape,
                tier=dec.tier,
                origin=meta.get("origin", "—"),
                origin_url=meta.get("origin_url", ""),
                how_it_works=meta.get("how_it_works", ""),
                example=meta.get("example"),
            )
        )
    infos.sort(key=lambda i: (i.kind != "deterministic", i.id))
    return infos


@app.get("/api/health")
def health() -> dict:
    settings = get_settings()
    pool = get_pool()
    return {
        "status": "ok",
        "tokens_configured": len(settings.token_pool),
        "small_model": settings.small_model,
        "large_model": settings.large_model,
        "judge_model": settings.resolved_judge_model,
        "llm_available": pool.has_tokens,
        "decomposers": list(REGISTRY.keys()),
    }


@app.get("/api/decomposers", response_model=list[DecomposerInfo])
def list_decomposers() -> list[DecomposerInfo]:
    return _catalog()


@app.get("/api/sample-queries")
def sample_queries() -> list[dict]:
    return _SAMPLES


@app.post("/api/compare", response_model=CompareResponse)
def compare(req: CompareRequest) -> CompareResponse:
    settings = get_settings()
    pool = get_pool()

    ids = req.decomposer_ids or list(REGISTRY.keys())
    unknown = [i for i in ids if i not in REGISTRY]
    if unknown:
        raise HTTPException(status_code=400, detail=f"unknown decomposer(s): {unknown}")

    needs_llm = any(REGISTRY[i].kind == "llm" for i in ids)
    if needs_llm and not pool.has_tokens:
        raise HTTPException(
            status_code=503,
            detail="No Hugging Face tokens configured (set HF_TOKENS in backend/.env).",
        )

    def _run(dec_id: str) -> DecompositionResult:
        ctx = DecomposerContext(pool=pool, tier_override=req.tier_override)
        try:
            return REGISTRY[dec_id].run(req.query, ctx)
        except Exception as exc:  # noqa: BLE001 - isolate a single decomposer's failure
            return REGISTRY[dec_id]._error_result(f"unhandled error: {exc}")

    with ThreadPoolExecutor(max_workers=min(8, len(ids))) as ex:
        results = list(ex.map(_run, ids))

    judge_model = settings.resolved_judge_model if (req.judge and pool.has_tokens) else None
    if judge_model:
        with ThreadPoolExecutor(max_workers=min(8, len(results))) as ex:
            judged = ex.map(
                lambda r: judge_decomposition(pool, req.query, r, model=judge_model), results
            )
            for res, verdict in zip(results, judged):
                res.judge = verdict

    return CompareResponse(query=req.query, judge_model=judge_model, results=results)
