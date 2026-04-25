import { ArrowLeft, ExternalLink, MessageSquare } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Avatar } from "../components/Avatar";
import { GlassCard } from "../components/GlassCard";
import { Button } from "../components/ui/button";
import type { KOLDetailView } from "../types";

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

export function KOLProfilePage({ detail }: KOLProfilePageProps) {
  const navigate = useNavigate();
  const { kol, recentPosts, mentions, notes, trackedSince } = detail;
  const resolvedMentions = mentions.filter((mention) => mention.isResolved).length;

  const tags = [kol.category ? kol.category.replace(/_/g, " ") : null, kol.primaryAsset]
    .filter(Boolean)
    .map((value) => String(value));

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
              Profile signal
            </div>
            <div className="text-xs sm:text-sm text-white/60">
              Heuristic based on priority, coverage, and resolved mentions
            </div>
          </GlassCard>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 lg:gap-6 mb-6 sm:mb-8">
            <div className="text-center">
              <div className="text-2xl sm:text-3xl font-bold text-white mb-1">{recentPosts.length}</div>
              <div className="text-xs sm:text-sm text-white/60">Recent posts</div>
            </div>
            <div className="text-center">
              <div className="text-2xl sm:text-3xl font-bold text-white mb-1">{mentions.length}</div>
              <div className="text-xs sm:text-sm text-white/60">Mentions found</div>
            </div>
            <div className="text-center">
              <div className="text-2xl sm:text-3xl font-bold text-white mb-1">{resolvedMentions}</div>
              <div className="text-xs sm:text-sm text-white/60">Resolved mentions</div>
            </div>
            <div className="text-center">
              <div className="text-2xl sm:text-3xl font-bold text-white mb-1">
                {trackedSince ?? "recent"}
              </div>
              <div className="text-xs sm:text-sm text-white/60">Tracked since</div>
            </div>
          </div>
        </div>

        {notes ? (
          <div className="mb-6 sm:mb-8">
            <h2 className="text-xs sm:text-sm font-semibold text-white/80 uppercase tracking-wide mb-3 sm:mb-4">
              Notes
            </h2>
            <GlassCard className="p-4 sm:p-5">
              <p className="text-sm text-white/70 leading-relaxed">{notes}</p>
            </GlassCard>
          </div>
        ) : null}

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

        <div>
          <h2 className="text-xs sm:text-sm font-semibold text-white/80 uppercase tracking-wide mb-3 sm:mb-5">
            Extracted Mentions
          </h2>
          <GlassCard>
            {mentions.length > 0 ? (
              mentions.map((mention, index) => (
                <div
                  key={`${mention.postId ?? "mention"}-${mention.symbolText ?? index}`}
                  className="p-3 sm:p-4 lg:p-5 border-b border-white/5 last:border-b-0"
                >
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-full bg-white/5 border border-white/10 flex items-center justify-center flex-shrink-0">
                      <MessageSquare className="w-4 h-4 text-white/70" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        <span className="text-sm font-semibold text-white">
                          {mention.tokenSymbol ?? mention.symbolText ?? "Unresolved"}
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded text-xs border ${
                            mention.isResolved
                              ? "bg-green-500/10 border-green-500/30 text-green-300"
                              : "bg-amber-500/10 border-amber-500/30 text-amber-300"
                          }`}
                        >
                          {mention.isResolved ? "resolved" : "unresolved"}
                        </span>
                        <span className="text-xs text-white/40 capitalize">{mention.mentionType}</span>
                      </div>
                      <p className="text-xs text-white/60 leading-relaxed">{mention.text}</p>
                      <div className="flex flex-wrap gap-3 mt-2 text-xs text-white/50">
                        {mention.chainName ? <span>{mention.chainName}</span> : null}
                        {mention.contractAddress ? <span className="font-mono">{mention.contractAddress}</span> : null}
                        {mention.url ? (
                          <a
                            href={mention.url}
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
              ))
            ) : (
              <div className="p-4 text-sm text-white/60">No extracted mentions yet for this profile.</div>
            )}
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
