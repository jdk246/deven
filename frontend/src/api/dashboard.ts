import { apiFetchBaseUrl } from "../lib/env";

export type BackendHealth = {
  status: "ok";
};

export type AgentHealth = {
  status: "ok";
  agent_mode: "deterministic" | "openai";
  data_mode: "seed" | "live";
  openai_ready: boolean;
};

export type ValidationCheck = {
  name: string;
  status: "pass" | "warn" | "fail";
  expected: number | string;
  actual: number | string | null;
  fix_hint: string;
};

export type ValidationResponse = {
  status: "pass" | "warn" | "fail";
  checks: ValidationCheck[];
};

export type ChainOption = {
  chain_id: string;
  name: string;
  short_name: string;
  platform: string;
  enabled_by_default: boolean;
  enabled: boolean;
};

export type TrendingToken = {
  chain_id: string;
  chain_name: string;
  chain_short_name: string;
  contract_address: string;
  symbol: string | null;
  name: string | null;
  icon_url: string | null;
  price: number | null;
  percent_change_24h: number | null;
  volume_24h: number | null;
  liquidity: number | null;
  holders: number | null;
  risk_level_enum: string | null;
  kol_mention_count: number;
  smart_money_signal_count: number;
  attention_score: number | null;
  label: string | null;
  updated_at: string;
};

export type TrendingTokensResponse = {
  items: TrendingToken[];
  available_chains: ChainOption[];
};

export type InsightItem = {
  chain_id: string;
  chain_name: string;
  contract_address: string;
  symbol: string | null;
  name: string | null;
  market_score: number | null;
  kol_score: number | null;
  smart_money_score: number | null;
  safety_score: number | null;
  final_score: number | null;
  attention_score: number | null;
  label: string | null;
  summary: string | null;
  updated_at: string | null;
};

export type InsightsResponse = {
  items: InsightItem[];
};

export type KOLItem = {
  handle: string;
  display_name: string | null;
  category: string | null;
  priority: number | null;
  post_count: number;
  resolved_mention_count: number;
  wallet_count: number;
};

export type KOLsResponse = {
  data_mode: "seed" | "live";
  items: KOLItem[];
};

export type AgentExample = {
  title: string;
  description: string;
  endpoint: string;
  method: "GET" | "POST";
  request_body: Record<string, unknown> | null;
  expected_response_shape: Record<string, unknown>;
};

export type AgentExamplesResponse = {
  items: AgentExample[];
};

export type AgentQueryRequest = {
  message: string;
  chain_id?: string;
  debug?: boolean;
};

export type AgentQueryResponse = {
  answer: string;
  evidence_used: Array<Record<string, unknown>>;
  missing_data: string[];
  tool_trace: Array<Record<string, unknown>>;
  disclaimer: string;
};

export type AdminRefreshRequest = {
  jobs?: Array<"market" | "audits" | "smart_money" | "kols" | "insights">;
  chains?: string[];
  limit_per_chain?: number;
};

export type AdminRefreshResponse = {
  status: "ok";
  jobs: string[];
  chains: ChainOption[];
  limit_per_chain: number;
  summary: Array<{
    chain_id: string;
    chain_name: string;
    tokens_seen: number;
    tokens_upserted: number;
    snapshots_created: number;
    audits_created: number;
    signals_upserted: number;
    errors: string[];
  }>;
  kol_summary?: {
    mode: "seed" | "live";
    profiles_seen: number;
    profiles_upserted: number;
    wallets_upserted: number;
    posts_seen: number;
    posts_upserted: number;
    mentions_upserted: number;
    mentions_resolved: number;
    mentions_unresolved: number;
    errors: string[];
  } | null;
  insight_summary?: {
    tokens_seen: number;
    insights_created: number;
    errors: string[];
  } | null;
  errors: string[];
};

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiFetchBaseUrl}${path}`, init);

  if (!response.ok) {
    const details = await response.text().catch(() => "");
    throw new Error(
      `${init?.method ?? "GET"} ${path} failed with status ${response.status}${
        details ? `: ${details.slice(0, 220)}` : ""
      }`,
    );
  }

  return response.json() as Promise<T>;
}

export function fetchBackendHealth(): Promise<BackendHealth> {
  return fetchJson<BackendHealth>("/health");
}

export function fetchAgentHealth(): Promise<AgentHealth> {
  return fetchJson<AgentHealth>("/api/agent/health");
}

export function fetchValidation(): Promise<ValidationResponse> {
  return fetchJson<ValidationResponse>("/api/admin/validate");
}

export function fetchTrendingTokens(limit = 12): Promise<TrendingTokensResponse> {
  return fetchJson<TrendingTokensResponse>(`/api/tokens/trending?limit=${limit}`);
}

export function fetchInsights(limit = 8): Promise<InsightsResponse> {
  return fetchJson<InsightsResponse>(`/api/insights?limit=${limit}`);
}

export function fetchKOLs(): Promise<KOLsResponse> {
  return fetchJson<KOLsResponse>("/api/kols");
}

export function fetchAgentExamples(): Promise<AgentExamplesResponse> {
  return fetchJson<AgentExamplesResponse>("/api/agent/examples");
}

export function queryAgent(payload: AgentQueryRequest): Promise<AgentQueryResponse> {
  return fetchJson<AgentQueryResponse>("/api/agent/query", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function runAdminRefresh(
  payload: AdminRefreshRequest = {},
): Promise<AdminRefreshResponse> {
  return fetchJson<AdminRefreshResponse>("/api/admin/refresh", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      jobs: payload.jobs ?? ["market", "audits", "smart_money", "kols", "insights"],
      chains: payload.chains,
      limit_per_chain: payload.limit_per_chain ?? 20,
    }),
  });
}
