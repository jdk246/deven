import { apiBaseUrl } from "../lib/env";

export type AgentHealthResponse = {
  status: "ok";
  agent_mode: "deterministic" | "openai";
  data_mode: "seed" | "live";
  openai_ready: boolean;
};

export type ValidationCheckResponse = {
  name: string;
  status: "pass" | "warn" | "fail";
  expected: number | string;
  actual: number | string | null;
  fix_hint: string;
};

export type ValidationResponse = {
  status: "pass" | "warn" | "fail";
  checks: ValidationCheckResponse[];
};

export type ChainOptionResponse = {
  chain_id: string;
  name: string;
  short_name: string;
  platform: string;
  enabled_by_default: boolean;
  enabled: boolean;
};

export type TokenListItemResponse = {
  chain_id: string;
  chain_name: string;
  chain_short_name: string;
  contract_address: string;
  symbol: string | null;
  name: string | null;
  icon_url: string | null;
  latest_price: number | null;
  latest_percent_change_24h: number | null;
  latest_volume_24h: number | null;
  latest_market_cap: number | null;
  holders: number | null;
  risk_level_enum: string | null;
  risk_level: number | null;
  latest_snapshot_at: string | null;
  latest_audit_at: string | null;
  updated_at: string | null;
};

export type TokenListResponse = {
  items: TokenListItemResponse[];
  available_chains: ChainOptionResponse[];
};

export type TrendingTokenResponse = {
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
  updated_at: string | null;
};

export type TrendingTokensResponse = {
  items: TrendingTokenResponse[];
  available_chains: ChainOptionResponse[];
};

export type InsightItemResponse = {
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
  items: InsightItemResponse[];
};

export type KOLListItemResponse = {
  handle: string;
  display_name: string | null;
  category: string | null;
  priority: number | null;
  post_count: number;
  resolved_mention_count: number;
  wallet_count: number;
};

export type KOLListResponse = {
  data_mode: "seed" | "live";
  items: KOLListItemResponse[];
};

export type KOLFeedMentionResponse = {
  mention_type: string;
  symbol_text: string | null;
  chain_id: string | null;
  chain_name: string | null;
  contract_address: string | null;
  is_resolved: boolean;
  confidence: number | null;
};

export type KOLFeedItemResponse = {
  post_id: number;
  external_post_id: string | null;
  created_at: string;
  text: string;
  url: string | null;
  like_count: number | null;
  repost_count: number | null;
  reply_count: number | null;
  view_count: number | null;
  source_mode: string;
  sentiment: string | null;
  sentiment_score: number | null;
  kol: {
    handle: string;
    display_name: string | null;
    category: string | null;
    priority: number | null;
  };
  resolved_mention_count: number;
  mentions: KOLFeedMentionResponse[];
};

export type KOLFeedResponse = {
  data_mode: "seed" | "live";
  items: KOLFeedItemResponse[];
};

export type KOLDetailResponse = {
  profile: {
    handle: string;
    display_name: string | null;
    category: string | null;
    priority: number | null;
    notes: string | null;
    created_at: string | null;
    updated_at: string | null;
    data_mode: "seed" | "live";
  };
  wallets: Array<{
    chain_id: string;
    chain_name: string;
    address: string;
    source_type: string | null;
    source_url: string | null;
    confidence: number | null;
    created_at: string | null;
  }>;
  recent_posts: Array<{
    id: number;
    external_post_id: string | null;
    created_at: string;
    text: string;
    url: string | null;
    like_count: number | null;
    repost_count: number | null;
    reply_count: number | null;
    view_count: number | null;
    source_mode: string;
    sentiment: string | null;
    sentiment_score: number | null;
    resolved_mention_count: number;
  }>;
  mentions: Array<{
    post_id: number;
    post_created_at: string | null;
    chain_id: string | null;
    chain_name: string | null;
    contract_address: string | null;
    symbol_text: string | null;
    mention_type: string;
    is_resolved: boolean;
    confidence: number | null;
    token_symbol: string | null;
    token_name: string | null;
    sentiment: string | null;
    text: string | null;
    url: string | null;
  }>;
};

export type TokenDetailResponse = {
  token: {
    chain_id: string;
    chain_name: string;
    chain_short_name: string;
    contract_address: string;
    symbol: string | null;
    name: string | null;
    icon_url: string | null;
    decimals: number | null;
    links: Array<{ label: string; link: string }>;
    first_seen_at: string | null;
    updated_at: string | null;
  };
  latest_market: {
    ts: string | null;
    price: number | null;
    percent_change_1h: number | null;
    percent_change_4h: number | null;
    percent_change_24h: number | null;
    volume_24h: number | null;
    liquidity: number | null;
    market_cap: number | null;
    fdv: number | null;
    holders: number | null;
    top10_holders_pct: number | null;
    kol_holders: number | null;
    kol_holding_pct: number | null;
    smart_money_holding_pct: number | null;
  } | null;
  audit: {
    ts: string | null;
    has_result: boolean;
    is_supported: boolean;
    risk_level_enum: string | null;
    risk_level: number | null;
    buy_tax: number | null;
    sell_tax: number | null;
    is_verified: boolean | null;
    risk_items: Array<{
      id: string;
      name: string;
      description: string | null;
      details: Array<{
        title: string;
        description: string | null;
        isHit: boolean;
        order: number | null;
        riskType: string | null;
      }>;
    }>;
  } | null;
  smart_money_signals: Array<{
    signal_id: string;
    chain_id: string;
    contract_address: string;
    ticker: string | null;
    direction: string | null;
    smart_money_count: number | null;
    signal_trigger_time: string | null;
    total_token_value: number | null;
    alert_price: number | null;
    current_price: number | null;
    highest_price: number | null;
    exit_rate: number | null;
    status: string | null;
    max_gain: number | null;
    ts: string | null;
  }>;
  kol_mentions: Array<{
    post_id: number | null;
    post_created_at: string | null;
    chain_id: string | null;
    chain_name: string | null;
    contract_address: string | null;
    symbol_text: string | null;
    mention_type: string;
    is_resolved: boolean;
    confidence: number | null;
    token_symbol: string | null;
    token_name: string | null;
    sentiment: string | null;
    text: string | null;
    url: string | null;
  }>;
  insight: {
    score_name: string;
    market_score: number | null;
    kol_score: number | null;
    smart_money_score: number | null;
    safety_score: number | null;
    final_score: number | null;
    attention_score: number | null;
    label: string | null;
    summary: string | null;
    generated_at: string | null;
    source_freshness: {
      market_snapshot_at: string | null;
      audit_at: string | null;
      latest_kol_post_at: string | null;
      latest_smart_money_at: string | null;
    };
    rationale: {
      risk_warnings?: string[];
    };
  } | null;
  source_freshness: {
    market_snapshot_at: string | null;
    audit_at: string | null;
    latest_smart_money_at: string | null;
    latest_kol_post_at: string | null;
    insight_at: string | null;
    kol_data_mode: "seed" | "live";
  };
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

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, init);

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

export function fetchAgentHealth(): Promise<AgentHealthResponse> {
  return fetchJson<AgentHealthResponse>("/api/agent/health");
}

export function fetchValidation(): Promise<ValidationResponse> {
  return fetchJson<ValidationResponse>("/api/admin/validate");
}

export function fetchTokenList(limit = 100): Promise<TokenListResponse> {
  return fetchJson<TokenListResponse>(`/api/tokens?limit=${limit}`);
}

export function fetchTrendingTokens(limit = 50): Promise<TrendingTokensResponse> {
  return fetchJson<TrendingTokensResponse>(`/api/tokens/trending?limit=${limit}`);
}

export function fetchInsights(limit = 50): Promise<InsightsResponse> {
  return fetchJson<InsightsResponse>(`/api/insights?limit=${limit}`);
}

export function fetchKOLs(): Promise<KOLListResponse> {
  return fetchJson<KOLListResponse>("/api/kols");
}

export function fetchKOLFeed(limit = 40): Promise<KOLFeedResponse> {
  return fetchJson<KOLFeedResponse>(`/api/kols/feed?limit=${limit}`);
}

export function fetchKOLDetail(handle: string): Promise<KOLDetailResponse> {
  return fetchJson<KOLDetailResponse>(`/api/kols/${encodeURIComponent(handle.replace(/^@/, ""))}`);
}

export function fetchTokenDetail(
  chainId: string,
  contractAddress: string,
): Promise<TokenDetailResponse> {
  return fetchJson<TokenDetailResponse>(
    `/api/tokens/${encodeURIComponent(chainId)}/${encodeURIComponent(contractAddress)}`,
  );
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
