import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import type { CompareResponse } from "./types";

interface SessionState {
  runs: CompareResponse[];
  addRun: (r: CompareResponse) => void;
  clear: () => void;
}

const Ctx = createContext<SessionState | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [runs, setRuns] = useState<CompareResponse[]>([]);
  const value = useMemo<SessionState>(
    () => ({
      runs,
      addRun: (r) => setRuns((prev) => [...prev, r]),
      clear: () => setRuns([]),
    }),
    [runs],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSession(): SessionState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useSession outside provider");
  return v;
}

export interface AggregateRow {
  decomposer_id: string;
  runs: number;
  errors: number;
  avgOverall: number;
  avgCoverage: number;
  avgMinimality: number;
  avgFaithfulness: number;
  avgStandalone: number;
  avgDependency: number;
  avgSubqueries: number;
  avgDepth: number;
  avgWidth: number;
  avgLatencyMs: number;
}

export function aggregate(runs: CompareResponse[]): AggregateRow[] {
  const acc = new Map<
    string,
    {
      n: number;
      errors: number;
      overall: number;
      judged: number;
      cov: number;
      min: number;
      faith: number;
      stand: number;
      dep: number;
      sq: number;
      depth: number;
      width: number;
      lat: number;
    }
  >();

  for (const run of runs) {
    for (const r of run.results) {
      const e =
        acc.get(r.decomposer_id) ??
        {
          n: 0,
          errors: 0,
          overall: 0,
          judged: 0,
          cov: 0,
          min: 0,
          faith: 0,
          stand: 0,
          dep: 0,
          sq: 0,
          depth: 0,
          width: 0,
          lat: 0,
        };
      e.n += 1;
      if (r.error) {
        e.errors += 1;
      } else {
        e.sq += r.subqueries.length;
        e.depth += r.stats?.depth ?? 0;
        e.width += r.stats?.max_width ?? 0;
        e.lat += r.latency_ms;
        if (r.judge && !r.judge.error) {
          e.judged += 1;
          e.overall += r.judge.overall;
          e.cov += r.judge.coverage.score;
          e.min += r.judge.minimality.score;
          e.faith += r.judge.faithfulness.score;
          e.stand += r.judge.standalone_answerability.score;
          e.dep += r.judge.dependency_correctness.score;
        }
      }
      acc.set(r.decomposer_id, e);
    }
  }

  const rows: AggregateRow[] = [];
  for (const [id, e] of acc) {
    const ok = Math.max(e.n - e.errors, 1);
    const j = Math.max(e.judged, 1);
    rows.push({
      decomposer_id: id,
      runs: e.n,
      errors: e.errors,
      avgOverall: e.judged ? e.overall / j : 0,
      avgCoverage: e.judged ? e.cov / j : 0,
      avgMinimality: e.judged ? e.min / j : 0,
      avgFaithfulness: e.judged ? e.faith / j : 0,
      avgStandalone: e.judged ? e.stand / j : 0,
      avgDependency: e.judged ? e.dep / j : 0,
      avgSubqueries: e.sq / ok,
      avgDepth: e.depth / ok,
      avgWidth: e.width / ok,
      avgLatencyMs: e.lat / ok,
    });
  }
  rows.sort((a, b) => b.avgOverall - a.avgOverall);
  return rows;
}
