import { useEffect, useMemo, useState } from "react";
import ResultPanel from "../components/ResultPanel";
import { compare, getDecomposers, getHealth, getSampleQueries, type HealthInfo } from "../api";
import { useSession } from "../session";
import type { CompareResponse, DecomposerInfo, SampleQuery } from "../types";

export default function Playground() {
  const { addRun } = useSession();
  const [decomposers, setDecomposers] = useState<DecomposerInfo[]>([]);
  const [samples, setSamples] = useState<SampleQuery[]>([]);
  const [health, setHealth] = useState<HealthInfo | null>(null);

  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [tier, setTier] = useState<"" | "small" | "large">("");
  const [judge, setJudge] = useState(true);

  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [response, setResponse] = useState<CompareResponse | null>(null);

  useEffect(() => {
    getDecomposers()
      .then((d) => {
        setDecomposers(d);
        setSelected(new Set(d.map((x) => x.id)));
      })
      .catch((e) => setErr(String(e)));
    getSampleQueries().then(setSamples).catch(() => undefined);
    getHealth().then(setHealth).catch(() => undefined);
  }, []);

  const infoById = useMemo(
    () => Object.fromEntries(decomposers.map((d) => [d.id, d])),
    [decomposers],
  );

  const toggle = (id: string) =>
    setSelected((prev) => {
      const n = new Set(prev);
      n.has(id) ? n.delete(id) : n.add(id);
      return n;
    });

  async function run() {
    if (!query.trim() || selected.size === 0) return;
    setLoading(true);
    setErr(null);
    try {
      const res = await compare({
        query: query.trim(),
        decomposer_ids: [...selected],
        tier_override: tier || null,
        judge,
      });
      setResponse(res);
      addRun(res);
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          rows={3}
          placeholder="Enter a complex query to decompose…"
          className="w-full resize-y rounded-lg border border-slate-300 p-3 text-sm outline-none focus:border-slate-500"
        />

        <div className="mt-2 flex flex-wrap gap-1.5">
          {samples.map((s) => (
            <button
              key={s.label}
              onClick={() => setQuery(s.query)}
              className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-[11px] text-slate-600 hover:bg-slate-100"
              title={s.query}
            >
              {s.label}
            </button>
          ))}
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-4">
          <label className="flex items-center gap-1.5 text-xs font-medium text-slate-600">
            Model tier
            <select
              value={tier}
              onChange={(e) => setTier(e.target.value as "" | "small" | "large")}
              className="rounded-md border border-slate-300 px-2 py-1 text-xs"
            >
              <option value="">per-method default</option>
              <option value="small">force small</option>
              <option value="large">force large</option>
            </select>
          </label>
          <label className="flex items-center gap-1.5 text-xs font-medium text-slate-600">
            <input type="checkbox" checked={judge} onChange={(e) => setJudge(e.target.checked)} />
            LLM-as-judge scoring
          </label>
          <button
            onClick={run}
            disabled={loading || !query.trim() || selected.size === 0}
            className="ml-auto rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
          >
            {loading ? "Running…" : `Compare ${selected.size} decomposer${selected.size === 1 ? "" : "s"}`}
          </button>
        </div>

        <div className="mt-3 flex flex-wrap gap-1.5 border-t border-slate-100 pt-3">
          {decomposers.map((d) => (
            <button
              key={d.id}
              onClick={() => toggle(d.id)}
              className={`rounded-md px-2 py-1 text-[11px] font-medium ${
                selected.has(d.id)
                  ? "bg-indigo-600 text-white"
                  : "bg-white text-slate-500 border border-slate-200"
              }`}
            >
              {d.name}
            </button>
          ))}
        </div>

        {health && (
          <div className="mt-2 text-[11px] text-muted">
            {health.tokens_configured} HF token(s) · small={health.small_model} · large=
            {health.large_model} · judge={health.judge_model}
            {judge && (
              <span className="ml-1 text-amber-600">
                — judge shares the large model, so large-tier methods may be mildly favoured.
              </span>
            )}
          </div>
        )}
      </div>

      {err && (
        <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {err}
        </div>
      )}

      {response && (
        <>
          <div className="mt-5 mb-2 text-sm text-slate-600">
            Results for <span className="font-semibold text-slate-900">“{response.query}”</span>
            {response.judge_model ? ` · judged by ${response.judge_model}` : " · not judged"}
          </div>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {[...response.results]
              .sort((a, b) => (b.judge?.overall ?? -1) - (a.judge?.overall ?? -1))
              .map((r) => (
                <ResultPanel key={r.decomposer_id} result={r} info={infoById[r.decomposer_id]} />
              ))}
          </div>
        </>
      )}
    </div>
  );
}
