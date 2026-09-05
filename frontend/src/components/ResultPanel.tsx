import { useState } from "react";
import DagView from "./DagView";
import JudgeCard from "./JudgeCard";
import type { DecomposerInfo, DecompositionResult } from "../types";

function Chip({ label, value }: { label: string; value: string | number }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">
      <span className="font-medium text-slate-500">{label}</span>
      <span className="font-semibold text-slate-800">{value}</span>
    </span>
  );
}

const SHAPE_COLOR: Record<string, string> = {
  dag: "bg-indigo-100 text-indigo-700",
  linear: "bg-sky-100 text-sky-700",
  flat: "bg-emerald-100 text-emerald-700",
  adaptive: "bg-amber-100 text-amber-700",
};

export default function ResultPanel({
  result,
  info,
}: {
  result: DecompositionResult;
  info?: DecomposerInfo;
}) {
  const [showRaw, setShowRaw] = useState(false);
  const s = result.stats;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="font-semibold text-slate-900">{info?.name ?? result.decomposer_id}</h3>
          <div className="text-[11px] text-muted">{info?.origin}</div>
        </div>
        <div className="flex flex-wrap justify-end gap-1">
          {info && (
            <span
              className={`rounded-md px-2 py-0.5 text-[11px] font-semibold ${
                SHAPE_COLOR[info.output_shape] ?? "bg-slate-100 text-slate-700"
              }`}
            >
              {info.output_shape}
            </span>
          )}
          {result.judge && !result.judge.error && (
            <span className="rounded-md bg-indigo-600 px-2 py-0.5 text-[11px] font-bold text-white">
              {result.judge.overall.toFixed(2)}
            </span>
          )}
        </div>
      </div>

      {result.error ? (
        <div className="mt-3 rounded-md border border-red-200 bg-red-50 p-2 text-xs text-red-700">
          {result.error}
        </div>
      ) : (
        <>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {s && <Chip label="subqueries" value={s.node_count} />}
            {s && <Chip label="edges" value={s.edge_count} />}
            {s && <Chip label="depth" value={s.depth} />}
            {s && <Chip label="parallelism" value={s.max_width} />}
            {s && <Chip label="decomposed" value={s.decomposed ? "yes" : "no"} />}
            <Chip label="latency" value={`${result.latency_ms} ms`} />
            {result.tokens ? <Chip label="tokens" value={result.tokens} /> : null}
          </div>

          {result.notes.length > 0 && (
            <div className="mt-2 text-[11px] text-slate-500">
              {result.notes.map((n, i) => (
                <div key={i}>• {n}</div>
              ))}
            </div>
          )}

          <ol className="mt-3 space-y-1 text-xs">
            {result.subqueries.map((q) => (
              <li key={q.id} className="flex gap-2">
                <span className="font-mono text-slate-400">{q.id}</span>
                <span className="text-slate-800">
                  {q.text}
                  {q.role ? <span className="ml-1 text-sky-600">[{q.role}]</span> : null}
                  {q.model_tier ? (
                    <span className="ml-1 text-violet-600">&lt;{q.model_tier}&gt;</span>
                  ) : null}
                </span>
              </li>
            ))}
          </ol>

          <div className="mt-3">
            <DagView result={result} />
          </div>

          {result.judge && (
            <div className="mt-3 border-t border-slate-100 pt-3">
              <JudgeCard judge={result.judge} />
            </div>
          )}

          {result.raw_output && (
            <div className="mt-3">
              <button
                className="text-[11px] font-medium text-slate-500 hover:text-slate-800"
                onClick={() => setShowRaw((v) => !v)}
              >
                {showRaw ? "▾ hide" : "▸ show"} raw model output
              </button>
              {showRaw && (
                <pre className="mt-1 max-h-56 overflow-auto rounded-md bg-slate-900 p-2 text-[11px] leading-relaxed text-slate-100">
                  {result.raw_output}
                </pre>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
