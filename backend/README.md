# Backend — Query Decomposer Arena

FastAPI service that runs several query decomposers on one query and scores each with a
reference-free LLM judge. No database — every request is stateless.

## Setup

Requires **Python 3.10+** (3.12 recommended).

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm      # for the rule-based decomposer
cp .env.example .env                         # then add your HF token(s)
uvicorn app.main:app --reload
```

## Configuration (`.env`)

| var | meaning |
|---|---|
| `HF_TOKENS` | comma/newline-separated Hugging Face tokens; used round-robin, rotated on HTTP 429/503. `HF_TOKEN` also works. |
| `SMALL_MODEL` / `LARGE_MODEL` | any model served by **HF Inference Providers** (routed via `router.huggingface.co`; the legacy `api-inference.huggingface.co` is retired). Defaults: `meta-llama/Llama-3.1-8B-Instruct` / `meta-llama/Llama-3.3-70B-Instruct`. |
| `JUDGE_MODEL` | judge model; blank ⇒ `LARGE_MODEL`. |
| `LLM_TIMEOUT_SECONDS`, `LLM_MAX_TOKENS` | per-call limits. |
| `FRONTEND_ORIGIN` | CORS origin for the Vite dev server. |

## API

| route | purpose |
|---|---|
| `GET /api/health` | token count, model tiers, decomposer ids |
| `GET /api/decomposers` | catalog metadata (name, kind, output shape, "how it works", source) |
| `GET /api/sample-queries` | bundled demo queries |
| `POST /api/compare` | `{query, decomposer_ids?, tier_override?, judge}` → per-decomposer sub-queries + edges + structural stats + judge scores. Decomposer failures are isolated per entry. |

## Decomposers (`app/decomposers/`)

`deterministic` (no LLM, spaCy) · `naive-small` / `naive-large` (same prompt, two tiers) ·
`llamaindex-subq` (flat) · `least-to-most`, `self-ask`, `r2-reasoner` (linear) ·
`hybridflow-eag` (validated DAG with repair + chain fallback) · `uno-orchestra` (adaptive).

Add one by subclassing `BaseDecomposer` in a new module and importing it in
`app/decomposers/__init__.py`; it self-registers. Give it an entry in
`app/data/catalog.json`.

Two guarantees enforced centrally in `BaseDecomposer._result` (so every decomposer
gets them for free):

- **Acyclic output.** Edges are pruned to real node ids, then `graph.break_cycles`
  drops the minimum-ish set of edges to make the graph a DAG; a note is added when it
  had to. `stats.is_dag` is therefore always `true` for a non-error result.
- **No invention.** Every LLM decomposer's system message is wrapped by
  `rule_system()`, which appends the shared `NO_INVENTION` rule — no method may add
  entities, names, numbers or constraints absent from the query. The judge's
  `faithfulness` criterion checks the same thing independently.

## Judge (`app/judge.py`)

Reference-free (no gold decompositions). One LLM call per decomposition scores five
criteria 1–5: coverage, minimality, faithfulness, standalone answerability, dependency
correctness. Structural facts (counts, depth, width, acyclicity) come from `app/graph.py`
and are not themselves scored. The judge uses the large model by default, so large-tier
decomposers may be mildly favoured — surfaced as a caveat in the UI.

## Tests

```bash
source .venv/bin/activate && pytest
```

Parser, graph-stats and HybridFlow repair/fallback tests all stub the LLM — no network.
