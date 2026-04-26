import {
  ArrowLeft,
  CheckCircle2,
  Clock3,
  ExternalLink,
  XCircle,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Avatar } from "../components/Avatar";
import { GlassCard } from "../components/GlassCard";
import { Button } from "../components/ui/button";
import type { Call, KOLDetailView } from "../types";

interface KOLProfilePageProps {
  detail: KOLDetailView;
}

function formatDate(timestamp: string) {
  const value = new Date(timestamp);
  if (Number.isNaN(value.getTime())) {
    return timestamp;
  }
  return value.toLocaleString();
}

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "N/A";
  }

  return `${value >= 0 ? "+" : ""}${value.toFixed(1)}%`;
}

function callStatus(call: Call) {
  if (call.outcome === "win") {
    return {
      icon: <CheckCircle2 className="w-4 h-4 text-green-400" />,
      label: "Aligned",
      tone: "text-green-400",
    };
  }

  if (call.outcome === "loss") {
    return {
      icon: <XCircle className="w-4 h-4 text-red-400" />,
      label: "Misaligned",
      tone: "text-red-400",
    };
  }

  return {
    icon: <Clock3 className="w-4 h-4 text-amber-400" />,
    label: "Pending",
    tone: "text-amber-400",
  };
}

export function KOLProfilePage({ detail }: KOLProfilePageProps) {
  const navigate = useNavigate();
  const {
    kol,
    recentPosts,
    mentions,
    trackedSince,
    trackRecord,
    callHistory,
    evaluatedCallHistory,
    pendingCallHistory,
  } = detail;

  const resolvedMentions = mentions.filter((mention) => mention.isResolved).length;
  const tags = [kol.category ? kol.category.replace(/_/g, " ") : null, kol.primaryAsset]
    .filter(Boolean)
    .map((value) => String(value));

  const alignmentSummary =
    trackRecord.sampleSizeConfidence >= 1
      ? "Established sample"
      : trackRecord.sampleSizeConfidence >= 0.6
        ? "Moderate sample"
        : trackRecord.sampleSizeConfidence > 0
          ? "Early sample"
          : "Insufficient sample";

  return (
    <div className="min-h-screen text-white relative z-10">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-10">
        <Button
          variant="ghost"
          className="mb-6 sm:mb-8 -ml-3 text-white/60 hover:text-white hover:bg-white/5 border-0"
          onClick={() => navigate(-1)}
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to feed
        </Button>

        <div className="mb-6 sm:mb-8">
          <div className="flex flex-col sm:flex-row items-start gap-3 sm:gap-4 mb-3 sm:mb-4">
            <Avatar initials={kol.initials} size="xl" tier={kol.tier} imageUrl={kol.avatarUrl} />
            <div className="flex-1 w-full sm:w-auto">
              <h1 className="text-2xl sm:text-3xl font-bold text-white mb-1">{kol.name}</h1>
              <div className="text-sm text-white/60 mb-2 sm:mb-3">{kol.handle}</div>
              <div className="flex flex-wrap gap-2">
                {tags.map((tag) => (
                  <span
                    key={tag}
                    className="px-2 sm:px-3 py-1 bg-white/5 border border-white/10 rounded-lg text-xs text-white/80 backdrop-blur-sm capitalize"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          </div>

          <GlassCard
            className={`p-6 sm:p-8 text-center mb-6 sm:mb-8 ${
              kol.tier === "good"
                ? "bg-gradient-to-br from-green-500/10 to-emerald-500/10 border-green-500/30"
                : kol.tier === "mixed"
                  ? "bg-gradient-to-br from-amber-500/10 to-orange-500/10 border-amber-500/30"
                  : "bg-gradient-to-br from-red-500/10 to-rose-500/10 border-red-500/30"
            }`}
          >
            <div
              className={`text-5xl sm:text-6xl lg:text-7xl font-bold mb-2 ${
                kol.tier === "good"
                  ? "text-green-400"
                  : kol.tier === "mixed"
                    ? "text-amber-400"
                    : "text-red-400"
              }`}
            >
              {kol.reliabilityScore}%
            </div>
            <div className="text-xs sm:text-sm text-white/80 uppercase tracking-wide mb-1">
              Track Record Score
            </div>
            <div className="text-xs sm:text-sm text-white/60">
              {trackRecord.hits} aligned vs {trackRecord.misses} misaligned evaluated calls
            </div>
          </GlassCard>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 lg:gap-6 mb-6 sm:mb-8">
            <div className="text-center">
              <div className="text-2xl sm:text-3xl font-bold text-white mb-1">{trackRecord.totalCalls}</div>
              <div className="text-xs sm:text-sm text-white/60">Total calls</div>
            </div>
            <div className="text-center">
              <div className="text-2xl sm:text-3xl font-bold text-white mb-1">{trackRecord.evaluatedCalls}</div>
              <div className="text-xs sm:text-sm text-white/60">Evaluated</div>
            </div>
            <div className="text-center">
              <div className="text-2xl sm:text-3xl font-bold text-white mb-1">
                {trackRecord.hitRate !== null ? `${Math.round(trackRecord.hitRate * 100)}%` : "N/A"}
              </div>
              <div className="text-xs sm:text-sm text-white/60">Hit rate</div>
            </div>
            <div className="text-center">
              <div
                className={`text-2xl sm:text-3xl font-bold mb-1 ${
                  (trackRecord.averageReturn24h ?? 0) >= 0 ? "text-green-400" : "text-red-400"
                }`}
              >
                {formatPercent(
                  trackRecord.averageReturn24h !== null ? trackRecord.averageReturn24h * 100 : null,
                )}
              </div>
              <div className="text-xs sm:text-sm text-white/60">Avg 24h return</div>
            </div>
          </div>
        </div>

        <div className="mb-6 sm:mb-8">
          <h2 className="text-xs sm:text-sm font-semibold text-white/80 uppercase tracking-wide mb-3 sm:mb-4">
            Historical Alignment
          </h2>
          <GlassCard className="p-4 sm:p-5">
            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
              <div className="flex-1">
                <div className="text-sm font-semibold text-white mb-2">{trackRecord.label}</div>
                <p className="text-sm text-white/70 leading-relaxed mb-3">
                  {kol.explanation ?? trackRecord.methodology}
                </p>
                <div className="flex flex-wrap gap-2 text-xs text-white/60">
                  <span className="px-2 py-1 rounded-lg bg-white/5 border border-white/10">
                    {alignmentSummary}
                  </span>
                  <span className="px-2 py-1 rounded-lg bg-white/5 border border-white/10">
                    {evaluatedCallHistory.length} evaluated shown
                  </span>
                  <span className="px-2 py-1 rounded-lg bg-white/5 border border-white/10">
                    {pendingCallHistory.length} pending shown
                  </span>
                  <span className="px-2 py-1 rounded-lg bg-white/5 border border-white/10">
                    {resolvedMentions} resolved mentions
                  </span>
                  {trackedSince ? (
                    <span className="px-2 py-1 rounded-lg bg-white/5 border border-white/10">
                      Tracked since {trackedSince}
                    </span>
                  ) : null}
                </div>
              </div>
              <div className="sm:max-w-[220px] text-xs text-white/55 leading-relaxed">
                {trackRecord.disclaimer}
              </div>
            </div>
          </GlassCard>
        </div>

        <div className="mb-6 sm:mb-8">
          <h2 className="text-xs sm:text-sm font-semibold text-white/80 uppercase tracking-wide mb-3 sm:mb-5">
            Recent Posts
          </h2>
          <GlassCard>
            {recentPosts.map((post) => (
              <div
                key={post.id}
                className="p-3 sm:p-4 lg:p-5 border-b border-white/5 last:border-b-0 hover:bg-white/5 transition-all duration-300"
              >
                <div className="flex flex-col sm:flex-row items-start gap-2 sm:gap-4">
                  <div className="flex-1 w-full sm:w-auto min-w-0">
                    <div className="flex flex-wrap items-center gap-2 sm:gap-3 mb-2">
                      <span className="text-xs sm:text-sm text-white/40">{formatDate(post.createdAt)}</span>
                      <span className="px-2 py-0.5 bg-purple-500/20 border border-purple-500/30 rounded text-xs text-purple-300 font-medium capitalize">
                        {post.sentiment}
                      </span>
                      <span className="text-xs text-white/50">{post.resolvedMentionCount} resolved mentions</span>
                    </div>
                    <p className="text-xs sm:text-sm text-white/80 leading-relaxed">{post.text}</p>
                    <div className="flex flex-wrap gap-3 mt-3 text-xs text-white/50">
                      <span>{post.likeCount} likes</span>
                      <span>{post.repostCount} reposts</span>
                      <span>{post.replyCount} replies</span>
                      <span>{post.viewCount} views</span>
                      {post.url ? (
                        <a
                          href={post.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-white/70 hover:text-white"
                        >
                          Open post
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      ) : null}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </GlassCard>
        </div>

        <div className="mb-6 sm:mb-8">
          <h2 className="text-xs sm:text-sm font-semibold text-white/80 uppercase tracking-wide mb-3 sm:mb-5">
            Call History
          </h2>
          <GlassCard>
            {callHistory.length > 0 ? (
              callHistory.map((call) => {
                const status = callStatus(call);
                return (
                  <div
                    key={call.id}
                    className="p-3 sm:p-4 lg:p-5 border-b border-white/5 last:border-b-0 hover:bg-white/5 transition-all duration-300"
                  >
                    <div className="flex flex-col sm:flex-row items-start gap-2 sm:gap-4">
                      <div className="flex-1 w-full sm:w-auto min-w-0">
                        <div className="flex flex-wrap items-center gap-2 sm:gap-3 mb-1 sm:mb-2">
                          <span className="text-xs sm:text-sm text-white/40">{formatDate(call.timestamp)}</span>
                          <span className="px-2 py-0.5 bg-purple-500/20 border border-purple-500/30 rounded text-xs text-purple-300 font-medium">
                            {call.symbol}
                          </span>
                          <span className="inline-flex items-center gap-1 text-xs text-white/60 capitalize">
                            {status.icon}
                            {status.label}
                          </span>
                          {call.priceWindow ? (
                            <span className="text-xs text-white/40">Window {call.priceWindow}</span>
                          ) : null}
                        </div>
                        <p className="text-xs sm:text-sm text-white/80 leading-relaxed">{call.snippet}</p>
                        <div className="flex flex-wrap gap-3 mt-3 text-xs text-white/50">
                          {call.chainName ? <span>{call.chainName}</span> : null}
                          {call.priceAtCall !== undefined ? <span>At post ${call.priceAtCall.toLocaleString()}</span> : null}
                          {call.currentPrice !== undefined ? <span>Observed ${call.currentPrice.toLocaleString()}</span> : null}
                          {call.sourceUrl ? (
                            <a
                              href={call.sourceUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 text-white/70 hover:text-white"
                            >
                              Open post
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          ) : null}
                        </div>
                      </div>
                      <div className={`text-xs sm:text-sm font-semibold flex-shrink-0 ${status.tone}`}>
                        {call.returnPct !== null && call.returnPct !== undefined
                          ? formatPercent(call.returnPct)
                          : status.label}
                      </div>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="p-4 text-sm text-white/60">
                No tracked call history is available for this profile yet.
              </div>
            )}
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
