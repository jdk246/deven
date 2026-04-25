import { Search } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Avatar } from "../components/Avatar";
import { GlassCard } from "../components/GlassCard";
import { ScorePill } from "../components/ScorePill";
import { Input } from "../components/ui/input";
import type { KOL } from "../types";

interface AllKOLsPageProps {
  kols: Record<string, KOL>;
}

export function AllKOLsPage({ kols }: AllKOLsPageProps) {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");

  const sortedKOLs = useMemo(
    () => Object.values(kols).sort((left, right) => right.reliabilityScore - left.reliabilityScore),
    [kols],
  );

  const filteredKOLs = sortedKOLs.filter((kol) => {
    const query = searchQuery.toLowerCase();
    return (
      kol.name.toLowerCase().includes(query) ||
      kol.handle.toLowerCase().includes(query) ||
      (kol.category ?? "").toLowerCase().includes(query)
    );
  });

  return (
    <div className="min-h-screen text-white relative z-10">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-10">
        <div className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold mb-3 bg-gradient-to-r from-white to-purple-200 bg-clip-text text-transparent">
            All KOLs
          </h1>
          <p className="text-sm sm:text-base text-white/60">
            Browse {sortedKOLs.length} monitored profiles
          </p>
        </div>

        <GlassCard className="p-3 sm:p-4 mb-6 sm:mb-8">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40 w-4 h-4 sm:w-5 sm:h-5" />
            <Input
              placeholder="Search KOLs by name, handle, or category..."
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              className="pl-9 sm:pl-10 text-sm sm:text-base bg-black/20 border-white/10 text-white placeholder:text-white/40 backdrop-blur-sm"
            />
          </div>
        </GlassCard>

        <GlassCard>
          {filteredKOLs.map((kol, index) => (
            <div
              key={kol.id}
              className="p-3 sm:p-4 lg:p-5 border-b border-white/5 last:border-b-0 hover:bg-white/5 cursor-pointer transition-all duration-300"
              onClick={() => navigate(`/kol/${kol.id}`)}
            >
              <div className="flex items-center gap-3 sm:gap-4 lg:gap-5">
                <div className="w-6 sm:w-8 text-white/40 font-medium text-xs sm:text-sm">
                  {String(index + 1).padStart(2, "0")}
                </div>
                <Avatar initials={kol.initials} size="md" tier={kol.tier} imageUrl={kol.avatarUrl} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 sm:gap-2 mb-0.5">
                    <span className="font-semibold text-sm sm:text-base text-white truncate">{kol.name}</span>
                  </div>
                  <div className="text-xs text-white/40 truncate">
                    {kol.handle} - {kol.primaryAsset} - {kol.callCount} posts
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  <ScorePill score={kol.reliabilityScore} tier={kol.tier} size="sm" />
                </div>
              </div>
            </div>
          ))}
        </GlassCard>
      </div>
    </div>
  );
}
