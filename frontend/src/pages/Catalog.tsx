import { useEffect, useMemo, useState } from "react";
import DecomposerCard from "../components/DecomposerCard";
import { getDecomposers } from "../api";
import type { DecomposerInfo, OutputShape } from "../types";

const SHAPES: (OutputShape | "all")[] = ["all", "dag", "linear", "flat", "adaptive"];
const KINDS = ["all", "deterministic", "llm"] as const;

export default function Catalog() {
  const [items, setItems] = useState<DecomposerInfo[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [shape, setShape] = useState<(typeof SHAPES)[number]>("all");
  const [kind, setKind] = useState<(typeof KINDS)[number]>("all");

  useEffect(() => {
    getDecomposers().then(setItems).catch((e) => setErr(String(e)));
  }, []);

  const filtered = useMemo(
    () =>
      items.filter(
        (i) =>
          (shape === "all" || i.output_shape === shape) &&
          (kind === "all" || i.kind === kind),
      ),
    [items, shape, kind],
  );

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-semibold text-slate-500">Shape</span>
          {SHAPES.map((s) => (
            <button
              key={s}
              onClick={() => setShape(s)}
              className={`rounded-md px-2 py-1 text-xs font-medium ${
                shape === s ? "bg-slate-900 text-white" : "bg-white text-slate-600 border border-slate-200"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-semibold text-slate-500">Kind</span>
          {KINDS.map((k) => (
            <button
              key={k}
              onClick={() => setKind(k)}
              className={`rounded-md px-2 py-1 text-xs font-medium ${
                kind === k ? "bg-slate-900 text-white" : "bg-white text-slate-600 border border-slate-200"
              }`}
            >
              {k}
            </button>
          ))}
        </div>
      </div>

      {err && <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{err}</div>}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filtered.map((i) => (
          <DecomposerCard key={i.id} info={i} />
        ))}
      </div>
    </div>
  );
}
