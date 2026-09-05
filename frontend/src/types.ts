export type ModelTier = "none" | "small" | "large";
export type OutputShape = "dag" | "linear" | "flat" | "adaptive";
export type DecomposerKind = "deterministic" | "llm";

export interface SubQuery {
  id: string;
  text: string;
  role?: string | null;
  model_tier?: ModelTier | null;
}

export interface Edge {
  from: string;
  to: string;
}

export interface GraphStats {
  node_count: number;
  edge_count: number;
  is_dag: boolean;
  depth: number;
  max_width: number;
  roots: number;
  leaves: number;
  decomposed: boolean;
}

export interface JudgeCriterion {
  score: number;
  rationale: string;
}

export interface JudgeResult {
  coverage: JudgeCriterion;
  minimality: JudgeCriterion;
  faithfulness: JudgeCriterion;
  standalone_answerability: JudgeCriterion;
  dependency_correctness: JudgeCriterion;
  overall: number;
  summary: string;
  error?: string | null;
}

export interface DecompositionResult {
  decomposer_id: string;
  subqueries: SubQuery[];
  edges: Edge[];
  stats: GraphStats | null;
  raw_output: string;
  model?: string | null;
  latency_ms: number;
  tokens?: number | null;
  notes: string[];
  error?: string | null;
  judge?: JudgeResult | null;
}

export interface CompareResponse {
  query: string;
  judge_model?: string | null;
  results: DecompositionResult[];
}

export interface DecomposerInfo {
  id: string;
  name: string;
  kind: DecomposerKind;
  output_shape: OutputShape;
  tier: ModelTier;
  origin: string;
  origin_url: string;
  how_it_works: string;
  example?: string | null;
}

export interface SampleQuery {
  label: string;
  query: string;
}

export const JUDGE_CRITERIA = [
  "coverage",
  "minimality",
  "faithfulness",
  "standalone_answerability",
  "dependency_correctness",
] as const;
export type JudgeCriterionKey = (typeof JUDGE_CRITERIA)[number];

export const CRITERION_LABEL: Record<JudgeCriterionKey, string> = {
  coverage: "Coverage",
  minimality: "Minimality",
  faithfulness: "Faithfulness",
  standalone_answerability: "Standalone",
  dependency_correctness: "Dependencies",
};
