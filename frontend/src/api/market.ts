import { apiBaseUrl } from "../lib/env";

export type ChainOption = {
  chain_id: string;
  name: string;
  short_name: string;
  platform: string;
  enabled_by_default: boolean;
  enabled: boolean;
};

export type TokenListItem = {
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
  updated_at: string;
};

export type TokenListResponse = {
  items: TokenListItem[];
  available_chains: ChainOption[];
};

export type RefreshRequest = {
  jobs?: Array<"market" | "audits" | "smart_money" | "kols" | "insights">;
  chains?: string[];
  limit_per_chain?: number;
};

export type RefreshResponse = {
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

export async function fetchTokens(chainId?: string): Promise<TokenListResponse> {
  const params = new URLSearchParams();
  if (chainId) {
    params.set("chain_id", chainId);
  }

  const url = `${apiBaseUrl}/api/tokens${params.toString() ? `?${params.toString()}` : ""}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Token request failed with status ${response.status}`);
  }

  return response.json() as Promise<TokenListResponse>;
}

export async function refreshMarket(payload: RefreshRequest = {}): Promise<RefreshResponse> {
  const response = await fetch(`${apiBaseUrl}/api/admin/refresh`, {
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

  if (!response.ok) {
    throw new Error(`Refresh request failed with status ${response.status}`);
  }

  return response.json() as Promise<RefreshResponse>;
}
