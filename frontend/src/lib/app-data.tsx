import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  fetchAgentHealth,
  fetchInsights,
  fetchKOLFeed,
  fetchKOLs,
  fetchTokenList,
  fetchTrendingTokens,
  fetchValidation,
} from "../api/trustTrace";
import { adaptAppSnapshot, tokenKey } from "./adapters";
import type { AppSnapshot, AssetData, KOL } from "../types";

type AppDataContextValue = {
  snapshot: AppSnapshot | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  getAssetByKey: (chainId: string, contractAddress: string) => AssetData | undefined;
  getKOLById: (handle: string) => KOL | undefined;
};

const AppDataContext = createContext<AppDataContextValue | null>(null);

export function AppDataProvider({ children }: { children: ReactNode }) {
  const [snapshot, setSnapshot] = useState<AppSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [agentHealth, validation, tokenList, trending, insights, kols, feed] =
        await Promise.all([
          fetchAgentHealth(),
          fetchValidation(),
          fetchTokenList(100),
          fetchTrendingTokens(50),
          fetchInsights(50),
          fetchKOLs(),
          fetchKOLFeed(40),
        ]);

      setSnapshot(
        adaptAppSnapshot({
          agentHealth,
          validation,
          tokenList,
          trending,
          insights,
          kols,
          feed,
        }),
      );
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Failed to load the TrustTrace app snapshot.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const value = useMemo<AppDataContextValue>(
    () => ({
      snapshot,
      loading,
      error,
      refresh: load,
      getAssetByKey: (chainId, contractAddress) =>
        snapshot?.assets[tokenKey(chainId, contractAddress)],
      getKOLById: (handle) => snapshot?.kols[handle.replace(/^@/, "")],
    }),
    [error, load, loading, snapshot],
  );

  return <AppDataContext.Provider value={value}>{children}</AppDataContext.Provider>;
}

export function useAppData() {
  const context = useContext(AppDataContext);

  if (!context) {
    throw new Error("useAppData must be used within AppDataProvider.");
  }

  return context;
}
