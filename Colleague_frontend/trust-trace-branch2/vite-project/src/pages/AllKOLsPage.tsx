import { Search } from 'lucide-react';
import { useState } from 'react';
import { KOL } from '../../types';
import { Avatar } from '../components/Avatar';
import { ScorePill } from '../components/ScorePill';
import { GlassCard } from '../components/GlassCard';
import { Input } from '../components/ui/input';
import { useNavigate } from 'react-router-dom';

interface AllKOLsPageProps {
  kols: Record<string, KOL>;
}

export function AllKOLsPage({ kols }: AllKOLsPageProps) {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');

  const sortedKOLs = Object.values(kols)
    .sort((a, b) => b.reliabilityScore - a.reliabilityScore);

  const filteredKOLs = sortedKOLs.filter(kol =>
    kol.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    kol.handle.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="min-h-screen text-white relative z-10">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-10">
        <div className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold mb-3 bg-gradient-to-r from-white to-purple-200 bg-clip-text text-transparent">
            All KOLs
          </h1>
          <p className="text-sm sm:text-base text-white/60">
            Browse and track {sortedKOLs.length} crypto influencers and analysts
          </p>
        </div>

        <GlassCard className="p-3 sm:p-4 mb-6 sm:mb-8">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40 w-4 h-4 sm:w-5 sm:h-5" />
            <Input
              placeholder="Search KOLs by name or handle..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
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
                  {String(index + 1).padStart(2, '0')}
                </div>
                <Avatar initials={kol.initials} size="md" tier={kol.tier} imageUrl={kol.avatarUrl} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 sm:gap-2 mb-0.5">
                    <span className="font-semibold text-sm sm:text-base text-white truncate">{kol.name}</span>
                    {kol.verified && (
                      <div className="w-3.5 h-3.5 sm:w-4 sm:h-4 rounded-full bg-gradient-to-br from-purple-500 to-violet-600 flex items-center justify-center shadow-lg shadow-purple-500/50 flex-shrink-0">
                        <svg className="w-2 h-2 sm:w-2.5 sm:h-2.5 text-white" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      </div>
                    )}
                  </div>
                  <div className="text-xs text-white/40 truncate">
                    {kol.handle} · {kol.primaryAsset} · {kol.callCount} calls
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
