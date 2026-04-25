import {
  ArrowLeft,
  ExternalLink,
  Link2,
  Shield,
  TrendingDown,
  TrendingUp,
  Waves,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

import { GlassCard } from "../components/GlassCard";
import { Button } from "../components/ui/button";
import type { MarketDetailView } from "../types";

interface AssetInsightsPageProps {
  detail: MarketDetailView;
}

function formatDate(value: string | null | undefined) {
  if (!value) {
    return "N/A";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "N/A";
  }

  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function formatCurrency(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "N/A";
  }

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: value >= 1 ? 2 : 6,
  }).format(value);
}

function ScoreCard({
  label,
  value,
}: {
  label: string;
  value: number | null;
}) {
  return (
    <GlassCard className="p-4">
      <div className="text-xs text-white/60 mb-1 uppercase tracking-wide">{label}</div>
      <div className="text-2xl font-bold text-white">{value !== null ? value.toFixed(0) : "N/A"}</div>
    </GlassCard>
  );
}

export function AssetInsightsPage({ detail }: AssetInsightsPageProps) {
  const navigate = useNavigate();
  const { asset, audit, smartMoneySignals, kolMentions } = detail;
  const isPositive = (asset.change24h ?? 0) > 0;

  return (
    <div className="min-h-screen text-white relative z-10">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-10">
        <Button
          variant="ghost"
          className="mb-6 sm:mb-8 -ml-3 text-white/60 hover:text-white hover:bg-white/5 border-0"
          onClick={() => navigate(-1)}
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>

        <GlassCard className="p-4 sm:p-6 lg:p-8 mb-4 sm:mb-6">
          <div className="flex items-center gap-3 sm:gap-4 mb-4 sm:mb-6">
            <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-gradient-to-br from-purple-500 to-violet-600 flex items-center justify-center text-white font-bold text-base sm:text-lg shadow-lg shadow-purple-500/50 overflow-hidden">
              {asset.iconUrl ? (
                <img src={asset.iconUrl} alt={asset.symbol} className="w-full h-full object-cover" />
              ) : (
                asset.symbol.substring(0, 3)
              )}
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-bold text-white">{asset.name}</h1>
              <div className="text-xs sm:text-sm text-white/60">
                {asset.symbol}, {asset.chainName}
              </div>
            </div>
          </div>

          <div className="mb-4 sm:mb-6">
            <div className="flex flex-wrap items-baseline gap-2 sm:gap-3 mb-2">
              <span className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white">
                {asset.price !== null && asset.price !== undefined
                  ? formatCurrency(asset.price)
                  : "N/A"}
              </span>
              <span
                className={`text-lg sm:text-xl font-semibold ${
                  isPositive ? "text-green-400" : "text-red-400"
                }`}
              >
                {formatPercent(asset.change24h)}
              </span>
              <span className="text-xs sm:text-sm text-white/60">24h</span>
            </div>
            <div className="flex flex-wrap gap-2">
              <span className="px-3 py-1 rounded-lg bg-white/5 border border-white/10 text-xs text-white/80">
                Attention {detail.attentionScore !== null ? detail.attentionScore.toFixed(1) : "N/A"}
              </span>
              {detail.label ? (
                <span className="px-3 py-1 rounded-lg bg-purple-500/10 border border-purple-500/20 text-xs text-purple-200">
                  {detail.label}
                </span>
              ) : null}
              {audit ? (
                <span className="px-3 py-1 rounded-lg bg-white/5 border border-white/10 text-xs text-white/80 capitalize">
                  Audit risk {audit.overallRisk}
                </span>
              ) : null}
            </div>
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 sm:gap-4 mb-4 sm:mb-6">
            <ScoreCard label="Attention" value={detail.attentionScore} />
            <ScoreCard label="Market" value={detail.scoreBreakdown.market} />
            <ScoreCard label="KOL" value={detail.scoreBreakdown.kol} />
            <ScoreCard label="Smart Money" value={detail.scoreBreakdown.smartMoney} />
            <ScoreCard label="Safety" value={detail.scoreBreakdown.safety} />
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-x-4 sm:gap-x-8 lg:gap-x-12 gap-y-3 sm:gap-y-4">
            <div>
              <div className="text-xs sm:text-sm text-white/60 mb-1">24h volume</div>
              <div className="text-lg sm:text-xl lg:text-2xl font-bold text-white">
                {formatCurrency(detail.latestMarket.volume24h)}
              </div>
            </div>
            <div>
              <div className="text-xs sm:text-sm text-white/60 mb-1">Liquidity</div>
              <div className="text-lg sm:text-xl lg:text-2xl font-bold text-white">
                {formatCurrency(detail.latestMarket.liquidity)}
              </div>
            </div>
            <div>
              <div className="text-xs sm:text-sm text-white/60 mb-1">Holders</div>
              <div className="text-lg sm:text-xl lg:text-2xl font-bold text-white">
                {detail.latestMarket.holders?.toLocaleString() ?? "N/A"}
              </div>
            </div>
            <div>
              <div className="text-xs sm:text-sm text-white/60 mb-1">Top 10 concentration</div>
              <div className="text-lg sm:text-xl lg:text-2xl font-bold text-white">
                {formatPercent(detail.latestMarket.top10HoldersPct)}
              </div>
            </div>
          </div>
        </GlassCard>

        <GlassCard className="p-4 sm:p-5 lg:p-6 mb-4 sm:mb-6 bg-gradient-to-br from-green-500/10 to-emerald-500/10 border-green-500/30">
          <div className="mb-2 sm:mb-3">
            <h2 className="text-xs font-semibold text-green-300 uppercase tracking-wide">
              Signal Summary
            </h2>
          </div>
          <h3 className="text-base sm:text-lg font-semibold text-white mb-2 sm:mb-3">
            Why this token has attention right now
          </h3>
          <p className="text-xs sm:text-sm text-white/80 leading-relaxed">{detail.summary}</p>
          <div className="flex flex-wrap gap-3 mt-4 text-xs text-white/50">
            <span>Market snapshot: {formatDate(detail.freshness.marketSnapshotAt)}</span>
            <span>Audit: {formatDate(detail.freshness.auditAt)}</span>
            <span>Insight: {formatDate(detail.freshness.insightAt)}</span>
          </div>
        </GlassCard>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6 mb-4 sm:mb-6">
          <GlassCard className="p-4 sm:p-5 lg:p-6">
            <div className="flex items-center gap-2 mb-4">
              <Waves className="w-4 h-4 text-purple-300" />
              <h2 className="text-xs sm:text-sm font-semibold text-white/80 uppercase tracking-wide">
                Smart Money Signals
              </h2>
            </div>
            {smartMoneySignals.length > 0 ? (
              <div className="space-y-3">
                {smartMoneySignals.map((signal) => (
                  <div key={signal.signalId} className="p-3 bg-white/5 border border-white/10 rounded-xl">
                    <div className="flex items-center justify-between gap-3 mb-2">
                      <span className="text-sm font-semibold text-white capitalize">
                        {signal.direction} signal
                      </span>
                      <span className="text-xs text-white/50">{formatDate(signal.signalTriggerTime)}</span>
                    </div>
                    <div className="grid grid-cols-2 gap-3 text-xs text-white/60">
                      <span>Participants: {signal.smartMoneyCount ?? "N/A"}</span>
                      <span>Alert: {formatCurrency(signal.alertPrice)}</span>
                      <span>Current: {formatCurrency(signal.currentPrice)}</span>
                      <span>Status: {signal.status ?? "N/A"}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-white/60">No stored smart-money signals for this token yet.</p>
            )}
          </GlassCard>

          <GlassCard className="p-4 sm:p-5 lg:p-6">
            <div className="flex items-center gap-2 mb-4">
              <Shield className="w-4 h-4 text-purple-300" />
              <h2 className="text-xs sm:text-sm font-semibold text-white/80 uppercase tracking-wide">
                Audit Checks
              </h2>
            </div>
            {audit ? (
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-white">{audit.name}</span>
                  <span className="px-2 py-0.5 rounded text-xs border bg-white/5 border-white/10 text-white/80 capitalize">
                    {audit.overallRisk} risk
                  </span>
                </div>
                {audit.checks.slice(0, 6).map((check) => (
                  <div key={check.id} className="p-3 bg-white/5 border border-white/10 rounded-xl">
                    <div className="flex items-center justify-between gap-3 mb-1">
                      <span className="text-sm text-white">{check.label}</span>
                      <span
                        className={`text-xs uppercase ${
                          check.status === "pass"
                            ? "text-green-400"
                            : check.status === "warning"
                              ? "text-amber-400"
                              : "text-red-400"
                        }`}
                      >
                        {check.status}
                      </span>
                    </div>
                    <p className="text-xs text-white/60">{check.detail}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-white/60">No stored audit data is available for this token yet.</p>
            )}
          </GlassCard>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
          <GlassCard className="p-4 sm:p-5 lg:p-6">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="w-4 h-4 text-purple-300" />
              <h2 className="text-xs sm:text-sm font-semibold text-white/80 uppercase tracking-wide">
                KOL Mentions
              </h2>
            </div>
            {kolMentions.length > 0 ? (
              <div className="space-y-3">
                {kolMentions.slice(0, 6).map((mention, index) => (
                  <div key={`${mention.postId ?? "mention"}-${index}`} className="p-3 bg-white/5 border border-white/10 rounded-xl">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="text-sm font-semibold text-white">
                        {mention.tokenSymbol ?? mention.symbolText ?? asset.symbol}
                      </span>
                      <span className="text-xs text-white/50 capitalize">{mention.mentionType}</span>
                      <span
                        className={`text-xs ${
                          mention.isResolved ? "text-green-400" : "text-amber-400"
                        }`}
                      >
                        {mention.isResolved ? "resolved" : "unresolved"}
                      </span>
                    </div>
                    <p className="text-xs text-white/60 leading-relaxed">{mention.text ?? "No mention text available."}</p>
                    <div className="flex flex-wrap gap-3 mt-2 text-xs text-white/50">
                      {mention.chainName ? <span>{mention.chainName}</span> : null}
                      {mention.sentiment ? <span>{mention.sentiment}</span> : null}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-white/60">No resolved KOL mentions are stored for this token right now.</p>
            )}
          </GlassCard>

          <GlassCard className="p-4 sm:p-5 lg:p-6">
            <div className="flex items-center gap-2 mb-4">
              <Link2 className="w-4 h-4 text-purple-300" />
              <h2 className="text-xs sm:text-sm font-semibold text-white/80 uppercase tracking-wide">
                Token Links
              </h2>
            </div>
            {detail.links.length > 0 ? (
              <div className="space-y-3">
                {detail.links.map((link) => (
                  <a
                    key={`${link.label}:${link.link}`}
                    href={link.link}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center justify-between gap-3 p-3 bg-white/5 border border-white/10 rounded-xl hover:bg-white/10 transition-colors"
                  >
                    <div>
                      <div className="text-sm font-semibold text-white capitalize">{link.label}</div>
                      <div className="text-xs text-white/50 truncate">{link.link}</div>
                    </div>
                    <ExternalLink className="w-4 h-4 text-white/60" />
                  </a>
                ))}
              </div>
            ) : (
              <p className="text-sm text-white/60">No external links were returned for this token.</p>
            )}
            <div className="mt-4 pt-4 border-t border-white/10 text-xs text-white/50 space-y-2">
              <div>Smart-money freshness: {formatDate(detail.freshness.latestSmartMoneyAt)}</div>
              <div>KOL freshness: {formatDate(detail.freshness.latestKolPostAt)}</div>
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
