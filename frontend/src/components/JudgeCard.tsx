import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from "recharts";
import {
  CRITERION_LABEL,
  JUDGE_CRITERIA,
  type JudgeResult,
} from "../types";

export default function JudgeCard({ judge }: { judge: JudgeResult }) {
  if (judge.error) {
    return (
      <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2">
        Judge: {judge.error}
      </div>
    );
  }

  const data = JUDGE_CRITERIA.map((k) => ({
    criterion: CRITERION_LABEL[k],
    score: judge[k].score,
  }));

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      <div className="h-44">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={data} outerRadius="72%">
            <PolarGrid />
            <PolarAngleAxis dataKey="criterion" tick={{ fontSize: 10 }} />
            <PolarRadiusAxis domain={[0, 5]} tick={{ fontSize: 9 }} tickCount={6} />
            <Radar dataKey="score" stroke="#6366f1" fill="#6366f1" fillOpacity={0.35} />
          </RadarChart>
        </ResponsiveContainer>
      </div>
      <div className="text-xs space-y-1.5">
        <div className="font-semibold text-sm">
          Overall {judge.overall.toFixed(2)} / 5
        </div>
        {JUDGE_CRITERIA.map((k) => (
          <div key={k}>
            <span className="font-medium">{CRITERION_LABEL[k]}: {judge[k].score}</span>
            <span className="text-muted"> — {judge[k].rationale}</span>
          </div>
        ))}
        {judge.summary ? (
          <div className="pt-1 text-slate-600 italic">{judge.summary}</div>
        ) : null}
      </div>
    </div>
  );
}
