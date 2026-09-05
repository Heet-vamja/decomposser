import type { DecomposerInfo } from "../types";

const SHAPE_COLOR: Record<string, string> = {
  dag: "bg-indigo-100 text-indigo-700",
  linear: "bg-sky-100 text-sky-700",
  flat: "bg-emerald-100 text-emerald-700",
  adaptive: "bg-amber-100 text-amber-700",
};

export default function DecomposerCard({ info }: { info: DecomposerInfo }) {
  return (
    <div className="flex h-full flex-col rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-semibold text-slate-900">{info.name}</h3>
        <div className="flex shrink-0 flex-wrap justify-end gap-1">
          <span
            className={`rounded-md px-2 py-0.5 text-[11px] font-semibold ${
              SHAPE_COLOR[info.output_shape] ?? "bg-slate-100 text-slate-700"
            }`}
          >
            {info.output_shape}
          </span>
          <span
            className={`rounded-md px-2 py-0.5 text-[11px] font-semibold ${
              info.kind === "deterministic"
                ? "bg-slate-200 text-slate-700"
                : "bg-fuchsia-100 text-fuchsia-700"
            }`}
          >
            {info.kind === "deterministic" ? "no LLM" : info.tier + " model"}
          </span>
        </div>
      </div>
      <div className="mt-0.5 text-[11px] text-muted">{info.origin}</div>
      <p className="mt-2 flex-1 text-xs leading-relaxed text-slate-700">{info.how_it_works}</p>
      {info.example && (
        <pre className="mt-2 whitespace-pre-wrap rounded-md bg-slate-50 p-2 text-[11px] text-slate-600">
          {info.example}
        </pre>
      )}
      {info.origin_url && (
        <a
          href={info.origin_url}
          target="_blank"
          rel="noreferrer"
          className="mt-2 text-[11px] font-medium text-indigo-600 hover:underline"
        >
          Source ↗
        </a>
      )}
    </div>
  );
}
