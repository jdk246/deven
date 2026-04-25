import { Circle, ExternalLink } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Avatar } from "../components/Avatar";
import { GlassCard } from "../components/GlassCard";
import { ScorePill } from "../components/ScorePill";
import type { Call, KOL } from "../types";

interface LiveFeedPageProps {
  calls: Call[];
  kols: Record<string, KOL>;
}

function formatTimestamp(timestamp: string) {
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const minutes = Math.floor(diff / (1000 * 60));

  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function LiveFeedPage({ calls, kols }: LiveFeedPageProps) {
  const navigate = useNavigate();

  const recentCalls = [...calls].sort(
    (left, right) => new Date(right.timestamp).getTime() - new Date(left.timestamp).getTime(),
  );

  return (
    <div className="min-h-screen text-white relative z-10">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-10">
        <div className="mb-6 sm:mb-8">
          <div className="flex items-center gap-2 sm:gap-3 mb-3 sm:mb-4">
            <Circle className="w-2.5 h-2.5 sm:w-3 sm:h-3 text-red-400 fill-red-400 animate-pulse" />
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold bg-gradient-to-r from-white to-purple-200 bg-clip-text text-transparent">
              Live Feed
            </h1>
          </div>
          <p className="text-sm sm:text-base text-white/60">
            Recent posts and token mentions across the monitored KOL set
          </p>
        </div>

        <GlassCard>
          {recentCalls.map((call) => {
            const kol = kols[call.kolId];
            if (!kol) return null;

            return (
              <div
                key={call.id}
                className="p-3 sm:p-4 lg:p-5 border-b border-white/5 last:border-b-0 hover:bg-white/5 cursor-pointer transition-all duration-300"
                onClick={() => navigate(`/kol/${kol.id}`)}
              >
                <div className="flex items-start gap-3 sm:gap-4">
                  <Avatar initials={kol.initials} size="md" tier={kol.tier} imageUrl={kol.avatarUrl} />
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 mb-1">
                      <span className="font-semibold text-sm sm:text-base text-white">{kol.name}</span>
                      <span className="text-xs sm:text-sm text-white/40">{kol.handle}</span>
                      <span className="text-xs sm:text-sm text-white/40">-</span>
                      <span className="text-xs sm:text-sm text-white/40">{formatTimestamp(call.timestamp)}</span>
                    </div>
                    <p className="text-xs sm:text-sm text-white/80 mb-2">{call.snippet}</p>
                    <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                      {call.chainId && call.contractAddress ? (
                        <button
                          onClick={(event) => {
                            event.stopPropagation();
                            navigate(
                              `/market/${encodeURIComponent(call.chainId!)}/${encodeURIComponent(call.contractAddress!)}`,
                            );
                          }}
                          className="px-2 py-0.5 bg-purple-500/20 border border-purple-500/30 rounded text-xs text-purple-300 font-medium hover:bg-purple-500/30 transition-colors"
                        >
                          {call.symbol}
                        </button>
                      ) : (
                        <span className="px-2 py-0.5 bg-white/5 border border-white/10 rounded text-xs text-white/70">
                          {call.symbol}
                        </span>
                      )}
                      <span className="text-xs text-white/40 capitalize">{call.type}</span>
                      {call.chainName ? <span className="text-xs text-white/40">{call.chainName}</span> : null}
                      {call.currentPrice !== undefined ? (
                        <span className="text-xs text-white/40">
                          ${call.currentPrice.toLocaleString()}
                        </span>
                      ) : null}
                      {call.engagement ? (
                        <span className="text-xs text-white/40">{call.engagement} engagement</span>
                      ) : null}
                      {call.sourceUrl ? (
                        <a
                          href={call.sourceUrl}
                          target="_blank"
                          rel="noreferrer"
                          onClick={(event) => event.stopPropagation()}
                          className="text-xs text-white/50 hover:text-white/80 inline-flex items-center gap-1"
                        >
                          Source
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      ) : null}
                    </div>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <ScorePill score={kol.reliabilityScore} tier={kol.tier} size="sm" />
                  </div>
                </div>
              </div>
            );
          })}
        </GlassCard>
      </div>
    </div>
  );
}
