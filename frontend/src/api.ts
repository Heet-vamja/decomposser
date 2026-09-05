import type {
  CompareResponse,
  DecomposerInfo,
  SampleQuery,
} from "./types";

const BASE = import.meta.env.VITE_API_BASE ?? "";

async function jget<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export interface HealthInfo {
  status: string;
  tokens_configured: number;
  small_model: string;
  large_model: string;
  judge_model: string;
  llm_available: boolean;
  decomposers: string[];
}

export const getHealth = () => jget<HealthInfo>("/api/health");
export const getDecomposers = () => jget<DecomposerInfo[]>("/api/decomposers");
export const getSampleQueries = () => jget<SampleQuery[]>("/api/sample-queries");

export interface CompareArgs {
  query: string;
  decomposer_ids?: string[];
  tier_override?: "small" | "large" | null;
  judge: boolean;
}

export async function compare(args: CompareArgs): Promise<CompareResponse> {
  const res = await fetch(`${BASE}/api/compare`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(args),
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<CompareResponse>;
}
