import { useEffect, useState } from "react";
import { Routes, Route, useParams } from "react-router-dom";

import { fetchKOLDetail, fetchTokenDetail } from "./api/trustTrace";
import { ChatBot } from "./components/ChatBot";
import { Sidebar } from "./components/Sidebar";
import { adaptKolDetail, adaptMarketDetail, adaptTokenAudit } from "./lib/adapters";
import { AppDataProvider, useAppData } from "./lib/app-data";
import { AllKOLsPage } from "./pages/AllKOLsPage";
import { AllMarketsPage } from "./pages/AllMarketsPage";
import { AssetInsightsPage } from "./pages/AssetInsightsPage";
import { DashboardPage } from "./pages/DashboardPage";
import { KOLProfilePage } from "./pages/KOLProfilePage";
import { LandingPage } from "./pages/LandingPage";
import { LiveFeedPage } from "./pages/LiveFeedPage";
import { TokenAuditPage } from "./pages/TokenAuditPage";
import type { AssetData, KOLDetailView, MarketDetailView, TokenAuditResult } from "./types";

function FullScreenState({
  title,
  message,
}: {
  title: string;
  message: string;
}) {
  return (
    <div className="min-h-screen text-white relative z-10 flex items-center justify-center px-6">
      <div className="text-center max-w-xl">
        <h1 className="text-3xl font-bold mb-3 bg-gradient-to-r from-white to-purple-200 bg-clip-text text-transparent">
          {title}
        </h1>
        <p className="text-white/60">{message}</p>
      </div>
    </div>
  );
}

function KOLProfileRoute() {
  const { handle } = useParams<{ handle: string }>();
  const [detail, setDetail] = useState<KOLDetailView | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadDetail() {
      if (!handle) {
        setError("Missing KOL handle.");
        return;
      }

      setError(null);
      setDetail(null);

      try {
        const response = await fetchKOLDetail(handle);
        if (!cancelled) {
          setDetail(adaptKolDetail(response));
        }
      } catch (caughtError) {
        if (!cancelled) {
          setError(caughtError instanceof Error ? caughtError.message : "Failed to load KOL profile.");
        }
      }
    }

    void loadDetail();
    return () => {
      cancelled = true;
    };
  }, [handle]);

  if (error) {
    return <FullScreenState title="KOL not available" message={error} />;
  }

  if (!detail) {
    return <FullScreenState title="Loading profile" message="Pulling the latest KOL profile and post activity." />;
  }

  return <KOLProfilePage detail={detail} />;
}

function AssetInsightsRoute() {
  const { chainId, contractAddress } = useParams<{ chainId: string; contractAddress: string }>();
  const [detail, setDetail] = useState<MarketDetailView | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadDetail() {
      if (!chainId || !contractAddress) {
        setError("Missing token route parameters.");
        return;
      }

      setError(null);
      setDetail(null);

      try {
        const response = await fetchTokenDetail(chainId, contractAddress);
        if (!cancelled) {
          setDetail(adaptMarketDetail(response));
        }
      } catch (caughtError) {
        if (!cancelled) {
          setError(caughtError instanceof Error ? caughtError.message : "Failed to load token detail.");
        }
      }
    }

    void loadDetail();
    return () => {
      cancelled = true;
    };
  }, [chainId, contractAddress]);

  if (error) {
    return <FullScreenState title="Token not available" message={error} />;
  }

  if (!detail) {
    return <FullScreenState title="Loading token" message="Pulling market, audit, and attention context." />;
  }

  return <AssetInsightsPage detail={detail} />;
}

function TokenAuditRoute() {
  const { snapshot } = useAppData();

  if (!snapshot) {
    return <FullScreenState title="Loading audit view" message="Preparing the monitored token list." />;
  }

  async function handleScan(asset: AssetData): Promise<TokenAuditResult | null> {
    const response = await fetchTokenDetail(asset.chainId, asset.contractAddress);
    return adaptTokenAudit(response);
  }

  return <TokenAuditPage assets={snapshot.assets} onScan={handleScan} />;
}

function AppRoutes() {
  const { snapshot, loading, error } = useAppData();

  if (loading && !snapshot) {
    return (
      <FullScreenState
        title="Loading TrustTrace"
        message="Loading market, social, and risk context."
      />
    );
  }

  if (error && !snapshot) {
    return (
      <FullScreenState
        title="Connection issue"
        message={error}
      />
    );
  }

  if (!snapshot) {
    return <FullScreenState title="No data available" message="TrustTrace could not load the latest system snapshot." />;
  }

  return (
    <Routes>
      <Route
        path="/"
        element={
          <LandingPage
            kols={snapshot.kols}
            feed={snapshot.feed}
            validationStatus={snapshot.validationStatus}
          />
        }
      />

      <Route
        path="/*"
        element={
          <div className="size-full flex">
            <Sidebar />
            <ChatBot />
            <div className="flex-1 lg:ml-64 relative z-10">
              <Routes>
                <Route
                  path="/dashboard"
                  element={
                    <DashboardPage
                      calls={snapshot.feed}
                      kols={snapshot.kols}
                      assets={snapshot.assets}
                      validationStatus={snapshot.validationStatus}
                    />
                  }
                />
                <Route
                  path="/live"
                  element={<LiveFeedPage calls={snapshot.feed} kols={snapshot.kols} />}
                />
                <Route path="/markets" element={<AllMarketsPage assets={snapshot.assets} />} />
                <Route path="/kols" element={<AllKOLsPage kols={snapshot.kols} />} />
                <Route path="/audit" element={<TokenAuditRoute />} />
                <Route path="/kol/:handle" element={<KOLProfileRoute />} />
                <Route path="/market/:chainId/:contractAddress" element={<AssetInsightsRoute />} />
                <Route
                  path="/settings"
                  element={
                    <FullScreenState
                      title="Settings"
                      message="Settings are not part of the current demo build yet."
                    />
                  }
                />
                <Route
                  path="*"
                  element={<FullScreenState title="404" message="That route does not exist in the current TrustTrace app." />}
                />
              </Routes>
            </div>
          </div>
        }
      />
    </Routes>
  );
}

export default function App() {
  return (
    <AppDataProvider>
      <AppRoutes />
    </AppDataProvider>
  );
}
