# Query Decomposer Arena

A full-stack demo that takes **one complex query** and shows how a range of published
**query decomposers** break it into **sub-queries + a dependency DAG** — side by side,
scored by an LLM judge.

Scope is decomposition only: produce the sub-queries and the graph, visualise them, and
score them. Sub-queries are **not** answered; there is no retrieval corpus and no
persistence (the scoreboard aggregates the current browser session).

## What's included

| Decomposer | Kind | Output shape | Source |
|---|---|---|---|
| Rule-based splitter | deterministic | flat (+ anaphora edges) | classic NLP / spaCy |
| Naive prompt — small model | LLM | linear | scale baseline |
| Naive prompt — large model | LLM | linear | scale baseline |
| LlamaIndex SubQuestionQueryEngine | LLM | flat / all-parallel | LlamaIndex |
| Least-to-Most prompting | LLM | linear chain | [arXiv:2205.10625](https://arxiv.org/abs/2205.10625) |
| Self-Ask | LLM | linear chain (dynamic) | [arXiv:2210.03350](https://arxiv.org/abs/2210.03350) |
| Route-and-Reason (R2-Reasoner) Task Decomposer | LLM | linear sequence + small/large routing | [arXiv:2506.05901](https://arxiv.org/abs/2506.05901) |
| HybridFlow — Explain-Analyze-Generate | LLM | **validated DAG** (repair + chain fallback) | [arXiv:2512.22137](https://arxiv.org/abs/2512.22137) |
| Uno-Orchestra | LLM | **adaptive** (may decline to decompose) | [arXiv:2605.05007](https://arxiv.org/abs/2605.05007) |

The LLM methods reproduce each paper's decomposition **prompt / procedure** for
inference only — no fine-tuning or RL checkpoints.

## App

- **Catalog** — filterable cards: how each method works, its output shape, source link.
- **Playground** — enter a query (or pick a sample), choose decomposers and a model tier,
  run. Each result shows the sub-query list, an auto-laid-out DAG, structural stats
  (depth, parallelism, acyclicity), latency/tokens, raw model output, and the judge's
  radar + rationales.
- **Scoreboard** — aggregates every comparison run this session into a ranked table +
  bar chart. Resets on reload.

## Judge

Reference-free LLM-as-judge, five criteria scored 1–5: **coverage**, **minimality**,
**faithfulness**, **standalone answerability**, **dependency correctness**. The judge
defaults to the large model; large-tier decomposers may be mildly favoured (noted in the UI).

## Run it

Two terminals.

```bash
# 1. backend  (Python 3.10+, 3.12 recommended)
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
cp .env.example .env            # add HF_TOKENS=hf_...   (HF Inference Providers)
uvicorn app.main:app --reload  # :8000
```

```bash
# 2. frontend
cd frontend
npm install
npm run dev                     # :5173  (proxies /api to :8000)
```

Open <http://localhost:5173>.

## Layout

```
backend/   FastAPI · app/decomposers/* · app/judge.py · app/graph.py · tests/
frontend/  React + Vite + TS · Tailwind · React Flow (DAG) · Recharts (scores)
```

See `backend/README.md` for the API and how to add a decomposer.

## Notes

- Hugging Face's legacy serverless endpoint (`api-inference.huggingface.co`) is retired;
  this project uses **Inference Providers** via `router.huggingface.co` (`provider="auto"`).
  Model availability there varies — swap `SMALL_MODEL` / `LARGE_MODEL` in `.env` if a
  default 404s.
- `HF_TOKENS` accepts many tokens; the backend round-robins and rotates on rate limits.
