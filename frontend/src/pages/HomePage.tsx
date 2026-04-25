import { CSSProperties, useEffect, useMemo, useState } from "react";

import { fetchHealth, type HealthResponse } from "../api/health";
import {
  fetchTokens,
  refreshMarket,
  type ChainOption,
  type TokenListItem,
} from "../api/market";
import { apiBaseUrl } from "../lib/env";

const sectionStyles: Record<string, CSSProperties> = {
  grid: {
    display: "grid",
    gap: "20px",
    gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
  },
  panel: {
    background: "rgba(10, 15, 31, 0.82)",
    border: "1px solid rgba(125, 211, 252, 0.18)",
    borderRadius: "8px",
    padding: "20px",
    boxShadow: "0 20px 60px rgba(0, 0, 0, 0.24)",
  },
  heading: {
    marginTop: 0,
    marginBottom: "8px",
    fontSize: "1.1rem",
  },
  text: {
    margin: 0,
    color: "#bfd0e4",
  },
  status: {
    display: "inline-flex",
    alignItems: "center",
    gap: "8px",
    padding: "6px 10px",
    borderRadius: "999px",
    background: "rgba(15, 23, 42, 0.9)",
    border: "1px solid rgba(148, 163, 184, 0.24)",
    marginBottom: "16px",
    fontSize: "0.95rem",
  },
  list: {
    margin: "12px 0 0",
    paddingLeft: "18px",
    color: "#d7e4f2",
  },
  code: {
    fontFamily: "Consolas, Monaco, monospace",
    color: "#7dd3fc",
  },
  toolbar: {
    display: "flex",
    flexWrap: "wrap",
    alignItems: "center",
    gap: "12px",
    marginBottom: "16px",
  },
  select: {
    minWidth: "180px",
    padding: "10px 12px",
    borderRadius: "8px",
    border: "1px solid rgba(148, 163, 184, 0.24)",
    background: "rgba(15, 23, 42, 0.9)",
    color: "#e5eef7",
  },
  button: {
    padding: "10px 14px",
    borderRadius: "8px",
    border: "1px solid rgba(125, 211, 252, 0.24)",
    background: "rgba(14, 116, 144, 0.22)",
    color: "#e5eef7",
    cursor: "pointer",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
  },
  cell: {
    padding: "12px 10px",
    borderTop: "1px solid rgba(148, 163, 184, 0.12)",
    textAlign: "left" as const,
    verticalAlign: "top" as const,
  },
  muted: {
    color: "#8ea4ba",
  },
  tokenName: {
    display: "grid",
    gap: "4px",
  },
  chainBadge: {
    display: "inline-flex",
    alignItems: "center",
    gap: "8px",
    padding: "6px 10px",
    borderRadius: "999px",
    background: "rgba(15, 23, 42, 0.9)",
    border: "1px solid rgba(125, 211, 252, 0.18)",
    fontSize: "0.85rem",
  },
};

export function HomePage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [tokens, setTokens] = useState<TokenListItem[]>([]);
  const [chains, setChains] = useState<ChainOption[]>([]);
  const [selectedChain, setSelectedChain] = useState<string>("");
  const [tokensError, setTokensError] = useState<string | null>(null);
  const [loadingTokens, setLoadingTokens] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshMessage, setRefreshMessage] = useState<string | null>(null);

  const selectedChainList = useMemo(
    () => (selectedChain ? [selectedChain] : undefined),
    [selectedChain],
  );

  async function loadTokens(chainId?: string) {
    setLoadingTokens(true);
    try {
      const payload = await fetchTokens(chainId);
      setTokens(payload.items);
      setChains(payload.available_chains);
      setTokensError(null);
    } catch (error) {
      setTokensError(error instanceof Error ? error.message : "Token load failed.");
    } finally {
      setLoadingTokens(false);
    }
  }

  async function handleRefresh() {
    setRefreshing(true);
    try {
      const result = await refreshMarket({
        chains: selectedChainList,
        limit_per_chain: 20,
      });
      const refreshedChains = result.summary.map((item) => item.chain_name).join(", ");
      const baseMessage = refreshedChains
        ? `Refresh completed for ${refreshedChains}.`
        : "Refresh completed.";
      const kolMessage = result.kol_summary
        ? ` KOL sync: ${result.kol_summary.profiles_upserted} profiles, ${result.kol_summary.posts_upserted} posts, and ${result.kol_summary.mentions_upserted} mentions.`
        : "";
      const insightMessage = result.insight_summary
        ? ` Insights: ${result.insight_summary.insights_created} summaries generated.`
        : "";
      setRefreshMessage(`${baseMessage}${kolMessage}${insightMessage}`);
      await loadTokens(selectedChain || undefined);
    } catch (error) {
      setRefreshMessage(
        error instanceof Error ? error.message : "Refresh request failed.",
      );
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => {
    let cancelled = false;

    fetchHealth()
      .then((payload) => {
        if (!cancelled) {
          setHealth(payload);
          setHealthError(null);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setHealthError("Backend not connected yet.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    void loadTokens(selectedChain || undefined);
  }, [selectedChain]);

  return (
    <section style={sectionStyles.grid}>
      <article style={sectionStyles.panel}>
        <h2 style={sectionStyles.heading}>Local services</h2>
        <div style={sectionStyles.status}>
          <strong>Frontend</strong>
          <span>http://localhost:5173</span>
        </div>
        <div style={sectionStyles.status}>
          <strong>Backend</strong>
          <span>{apiBaseUrl}</span>
        </div>
        <p style={sectionStyles.text}>
          The first chunk keeps things intentionally lean: bootable apps,
          predictable folders, and one health endpoint to verify the backend is
          reachable from the frontend.
        </p>
      </article>

      <article style={sectionStyles.panel}>
        <h2 style={sectionStyles.heading}>Backend health</h2>
        {health ? (
          <>
            <div style={sectionStyles.status}>
              <strong>{health.status}</strong>
              <span>FastAPI backend reachable</span>
            </div>
            <p style={sectionStyles.text}>
              Backend-driven data ingestion keeps Binance access off the
              frontend and gives us one place to persist market snapshots,
              audits, and smart-money rows.
            </p>
          </>
        ) : (
          <p style={sectionStyles.text}>{healthError ?? "Checking backend..."}</p>
        )}
      </article>

      <article style={sectionStyles.panel}>
        <h2 style={sectionStyles.heading}>Chain-aware token feed</h2>
        <div style={sectionStyles.toolbar}>
          <select
            value={selectedChain}
            onChange={(event) => setSelectedChain(event.target.value)}
            style={sectionStyles.select}
          >
            <option value="">All enabled chains</option>
            {chains.map((chain) => (
              <option key={chain.chain_id} value={chain.chain_id}>
                {chain.short_name} · {chain.name}
              </option>
            ))}
          </select>

          <button
            type="button"
            onClick={() => void handleRefresh()}
            disabled={refreshing}
            style={sectionStyles.button}
          >
            {refreshing ? "Refreshing..." : "Run ingestion"}
          </button>
        </div>

        {refreshMessage ? (
          <p style={sectionStyles.text}>{refreshMessage}</p>
        ) : null}

        {loadingTokens ? (
          <p style={sectionStyles.text}>Loading token feed...</p>
        ) : tokensError ? (
          <p style={sectionStyles.text}>{tokensError}</p>
        ) : tokens.length === 0 ? (
          <p style={sectionStyles.text}>
            No tokens ingested yet. Use the refresh button to pull Binance data
            through the backend.
          </p>
        ) : (
          <table style={sectionStyles.table}>
            <thead>
              <tr>
                <th style={sectionStyles.cell}>Token</th>
                <th style={sectionStyles.cell}>Chain</th>
                <th style={sectionStyles.cell}>Price</th>
                <th style={sectionStyles.cell}>24h</th>
                <th style={sectionStyles.cell}>Audit</th>
              </tr>
            </thead>
            <tbody>
              {tokens.map((token) => (
                <tr key={`${token.chain_id}:${token.contract_address}`}>
                  <td style={sectionStyles.cell}>
                    <div style={sectionStyles.tokenName}>
                      <strong>{token.symbol ?? "Unknown"}</strong>
                      <span style={sectionStyles.muted}>
                        {token.name ?? token.contract_address}
                      </span>
                    </div>
                  </td>
                  <td style={sectionStyles.cell}>
                    <span style={sectionStyles.chainBadge}>
                      {token.chain_short_name}
                    </span>
                  </td>
                  <td style={sectionStyles.cell}>
                    {token.latest_price !== null
                      ? `$${token.latest_price.toLocaleString()}`
                      : "—"}
                  </td>
                  <td style={sectionStyles.cell}>
                    {token.latest_percent_change_24h !== null
                      ? `${token.latest_percent_change_24h.toFixed(2)}%`
                      : "—"}
                  </td>
                  <td style={sectionStyles.cell}>
                    {token.risk_level_enum ?? "Unavailable"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </article>
    </section>
  );
}
