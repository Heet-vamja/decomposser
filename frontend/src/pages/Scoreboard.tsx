import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { aggregate, useSession } from "../session";

function n(x: number, d = 2) {
  return Number.isFinite(x) ? x.toFixed(d) : "—";
}

export default function Scoreboard() {
  const { runs, clear } = useSession();
  const rows = useMemo(() => aggregate(runs), [runs]);
  const totalRuns = runs.length;

  if (totalRuns === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-muted">
        No comparisons yet this session. Run some in the{" "}
        <span className="font-medium text-slate-700">Playground</span> — results aggregate here.
      </div>
    );
  }

  const chartData = rows.map((r) => ({
    name: r.decomposer_id,
    overall: Number(r.avgOverall.toFixed(2)),
  }));

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <div className="text-sm text-slate-600">
          Aggregated over <span className="font-semibold text-slate-900">{totalRuns}</span> comparison
          {totalRuns === 1 ? "" : "s"} this session.{" "}
          <span className="text-muted">Resets on reload (no persistence).</span>
        </div>
        <button
          onClick={clear}
          className="rounded-md border border-slate-300 px-3 py-1 text-xs font-medium text-slate-600 hover:bg-slate-100"
        >
          Clear session
        </button>
      </div>

      <div className="h-64 rounded-xl border border-slate-200 bg-white p-3">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 8, right: 12, bottom: 8, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 10 }} interval={0} angle={-20} textAnchor="end" height={60} />
            <YAxis domain={[0, 5]} tick={{ fontSize: 10 }} />
            <Tooltip />
            <Bar dataKey="overall" fill="#6366f1" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200 bg-white">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50 text-left text-slate-500">
              <th className="px-3 py-2">Decomposer</th>
              <th className="px-3 py-2">Runs</th>
              <th className="px-3 py-2">Err</th>
              <th className="px-3 py-2">Overall</th>
              <th className="px-3 py-2">Cover</th>
              <th className="px-3 py-2">Minim</th>
              <th className="px-3 py-2">Faith</th>
              <th className="px-3 py-2">Standln</th>
              <th className="px-3 py-2">Deps</th>
              <th className="px-3 py-2">Sub-q</th>
              <th className="px-3 py-2">Depth</th>
              <th className="px-3 py-2">Parallel</th>
              <th className="px-3 py-2">Latency</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.decomposer_id} className="border-b border-slate-100 last:border-0">
                <td className="px-3 py-2 font-medium text-slate-800">{r.decomposer_id}</td>
                <td className="px-3 py-2">{r.runs}</td>
                <td className="px-3 py-2">{r.errors || ""}</td>
                <td className="px-3 py-2 font-semibold text-indigo-700">{n(r.avgOverall)}</td>
                <td className="px-3 py-2">{n(r.avgCoverage, 1)}</td>
                <td className="px-3 py-2">{n(r.avgMinimality, 1)}</td>
                <td className="px-3 py-2">{n(r.avgFaithfulness, 1)}</td>
                <td className="px-3 py-2">{n(r.avgStandalone, 1)}</td>
                <td className="px-3 py-2">{n(r.avgDependency, 1)}</td>
                <td className="px-3 py-2">{n(r.avgSubqueries, 1)}</td>
                <td className="px-3 py-2">{n(r.avgDepth, 1)}</td>
                <td className="px-3 py-2">{n(r.avgWidth, 1)}</td>
                <td className="px-3 py-2">{Math.round(r.avgLatencyMs)} ms</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
