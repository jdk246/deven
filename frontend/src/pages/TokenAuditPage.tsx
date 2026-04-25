import {
  ArrowLeft,
  CheckCircle2,
  Search,
  Shield,
  AlertTriangle,
  XCircle,
} from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { GlassCard } from "../components/GlassCard";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import type { AssetData, TokenAuditResult } from "../types";

interface TokenAuditPageProps {
  assets: Record<string, AssetData>;
  onScan: (asset: AssetData) => Promise<TokenAuditResult | null>;
}

function getStatusIcon(status: "pass" | "warning" | "fail") {
  switch (status) {
    case "pass":
      return <CheckCircle2 className="w-5 h-5 text-green-400" />;
    case "warning":
      return <AlertTriangle className="w-5 h-5 text-yellow-400" />;
    case "fail":
      return <XCircle className="w-5 h-5 text-red-400" />;
  }
}

function getTrafficLight(risk: "low" | "medium" | "high") {
  return (
    <div className="flex gap-3">
      <div
        className={`w-14 h-14 rounded-full border-2 transition-all ${
          risk === "low"
            ? "bg-green-500 shadow-lg shadow-green-500/50 border-green-400"
            : "bg-white/5 border-white/10"
        }`}
      ></div>
      <div
        className={`w-14 h-14 rounded-full border-2 transition-all ${
          risk === "medium"
            ? "bg-yellow-500 shadow-lg shadow-yellow-500/50 border-yellow-400"
            : "bg-white/5 border-white/10"
        }`}
      ></div>
      <div
        className={`w-14 h-14 rounded-full border-2 transition-all ${
          risk === "high"
            ? "bg-red-500 shadow-lg shadow-red-500/50 border-red-400"
            : "bg-white/5 border-white/10"
        }`}
      ></div>
    </div>
  );
}

export function TokenAuditPage({ assets, onScan }: TokenAuditPageProps) {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [selectedAsset, setSelectedAsset] = useState<AssetData | null>(null);
  const [result, setResult] = useState<TokenAuditResult | null>(null);
  const [loading, setLoading] = useState(false);

  const assetList = useMemo(() => Object.values(assets), [assets]);
  const filteredAssets = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) {
      return assetList.slice(0, 8);
    }

    return assetList
      .filter(
        (asset) =>
          asset.symbol.toLowerCase().includes(normalized) ||
          asset.name.toLowerCase().includes(normalized) ||
          asset.contractAddress.toLowerCase().includes(normalized) ||
          asset.chainName.toLowerCase().includes(normalized),
      )
      .slice(0, 8);
  }, [assetList, query]);

  async function handleScan(asset = selectedAsset ?? filteredAssets[0] ?? null) {
    if (!asset) {
      return;
    }

    setSelectedAsset(asset);
    setLoading(true);

    try {
      const scanResult = await onScan(asset);
      setResult(scanResult);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen text-white relative z-10">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-10">
        <Button
          variant="ghost"
          className="mb-6 sm:mb-8 -ml-3 text-white/60 hover:text-white hover:bg-white/5 border-0"
          onClick={() => navigate(-1)}
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>

        <div className="mb-6 sm:mb-8">
          <div className="flex items-center gap-2 mb-3">
            <Shield className="w-5 h-5 sm:w-6 sm:h-6 text-purple-400" />
            <h1 className="text-2xl sm:text-3xl font-bold bg-gradient-to-r from-white to-purple-200 bg-clip-text text-transparent">
              Token Security Audit
            </h1>
          </div>
          <p className="text-sm sm:text-base text-white/60">
            Search monitored tokens by symbol, name, or contract. This view audits tokens already
            covered by TrustTrace.
          </p>
        </div>

        <GlassCard className="p-4 sm:p-5 lg:p-6 mb-6 sm:mb-8">
          <div className="mb-3 sm:mb-4">
            <label className="text-xs sm:text-sm text-white/80 mb-2 block">Tracked token</label>
            <div className="flex flex-col sm:flex-row gap-2 sm:gap-3">
              <Input
                placeholder="Search by symbol, name, or contract..."
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    void handleScan();
                  }
                }}
                className="flex-1 text-sm sm:text-base bg-black/20 border-white/10 text-white placeholder:text-white/40 backdrop-blur-sm"
              />
              <Button
                onClick={() => void handleScan()}
                className="w-full sm:w-auto bg-gradient-to-r from-purple-500 to-violet-600 hover:from-purple-600 hover:to-violet-700 text-white border-0 shadow-lg shadow-purple-500/30"
                disabled={loading}
              >
                <Search className="w-4 h-4 mr-2" />
                {loading ? "Scanning..." : "Scan"}
              </Button>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            {filteredAssets.map((asset) => (
              <button
                key={asset.key}
                type="button"
                onClick={() => {
                  setQuery(`${asset.symbol} ${asset.chainShortName}`);
                  setSelectedAsset(asset);
                  void handleScan(asset);
                }}
                className="px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-left hover:bg-white/10 transition-colors"
              >
                <div className="text-sm font-medium text-white">
                  {asset.symbol} - {asset.chainShortName}
                </div>
                <div className="text-xs text-white/50 truncate max-w-[220px]">{asset.contractAddress}</div>
              </button>
            ))}
          </div>
        </GlassCard>

        {result ? (
          <div className="space-y-4 sm:space-y-6">
            <GlassCard className="p-4 sm:p-6 lg:p-8">
              <div className="flex flex-col sm:flex-row items-start justify-between gap-4 sm:gap-6 lg:gap-8 mb-4 sm:mb-6">
                <div className="flex-1 w-full sm:w-auto">
                  <div className="flex flex-wrap items-center gap-2 sm:gap-3 mb-2 sm:mb-3">
                    <h2 className="text-xl sm:text-2xl lg:text-3xl font-bold bg-gradient-to-r from-white to-purple-200 bg-clip-text text-transparent">
                      {result.name}
                    </h2>
                    <span className="text-base sm:text-lg text-white/60">
                      {result.symbol} - {result.chainName}
                    </span>
                  </div>
                  <GlassCard className="font-mono text-xs text-white/60 break-all px-2 sm:px-3 py-1.5 sm:py-2 bg-black/20 mb-3 sm:mb-4">
                    {result.contract}
                  </GlassCard>
                  {result.summary ? <p className="text-sm text-white/70">{result.summary}</p> : null}
                </div>
                <div className="flex justify-center w-full sm:w-auto">{getTrafficLight(result.overallRisk)}</div>
              </div>
              <div
                className={`inline-flex items-center gap-2 px-3 sm:px-4 py-1.5 sm:py-2 rounded-lg text-xs sm:text-sm font-semibold border backdrop-blur-sm ${
                  result.overallRisk === "high"
                    ? "bg-red-500/20 text-red-400 border-red-500/30"
                    : result.overallRisk === "medium"
                      ? "bg-yellow-500/20 text-yellow-400 border-yellow-500/30"
                      : "bg-green-500/20 text-green-400 border-green-500/30"
                }`}
              >
                {result.overallRisk.toUpperCase()} RISK
              </div>
            </GlassCard>

            <div>
              <h2 className="text-xs sm:text-sm font-semibold text-white/80 uppercase tracking-wide mb-3 sm:mb-5">
                Security Checks
              </h2>
              <GlassCard>
                {result.checks.map((check, index) => {
                  const isLast = index === result.checks.length - 1;
                  return (
                    <div
                      key={check.id}
                      className={`p-3 sm:p-4 lg:p-5 ${!isLast ? "border-b border-white/5" : ""}`}
                    >
                      <div className="flex items-start gap-3 sm:gap-4">
                        <div
                          className={`w-8 h-8 sm:w-9 sm:h-9 rounded-full flex items-center justify-center flex-shrink-0 border backdrop-blur-sm ${
                            check.status === "pass"
                              ? "bg-green-500/20 border-green-500/30"
                              : check.status === "warning"
                                ? "bg-yellow-500/20 border-yellow-500/30"
                                : "bg-red-500/20 border-red-500/30"
                          }`}
                        >
                          {getStatusIcon(check.status)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 sm:gap-2 mb-1">
                            <div className="text-xs sm:text-sm font-semibold text-white">{check.label}</div>
                            <span
                              className={`text-xs uppercase tracking-wide font-medium ${
                                check.status === "pass"
                                  ? "text-green-400"
                                  : check.status === "warning"
                                    ? "text-yellow-400"
                                    : "text-red-400"
                              }`}
                            >
                              {check.status}
                            </span>
                          </div>
                          <div className="text-xs text-white/60">{check.detail}</div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </GlassCard>
            </div>

            <GlassCard
              className={`p-4 sm:p-5 lg:p-6 border ${
                result.overallRisk === "high"
                  ? "bg-gradient-to-r from-red-500/10 to-orange-500/10 border-red-500/30"
                  : result.overallRisk === "medium"
                    ? "bg-gradient-to-r from-yellow-500/10 to-orange-500/10 border-yellow-500/30"
                    : "bg-gradient-to-r from-green-500/10 to-emerald-500/10 border-green-500/30"
              }`}
            >
              <h3
                className={`text-xs sm:text-sm font-semibold mb-2 uppercase tracking-wide ${
                  result.overallRisk === "high"
                    ? "text-red-300"
                    : result.overallRisk === "medium"
                      ? "text-yellow-300"
                      : "text-green-300"
                }`}
              >
                Recommendation
              </h3>
              <p className="text-xs sm:text-sm text-white/70">{result.recommendation}</p>
            </GlassCard>
          </div>
        ) : null}
      </div>
    </div>
  );
}
