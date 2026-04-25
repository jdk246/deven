import { ArrowLeft, ExternalLink } from 'lucide-react';
import { KOL, Call } from '../../types';
import { Avatar } from '../components/Avatar';
import { GlassCard } from '../components/GlassCard';
import { Button } from '../components/ui/button';
import { useNavigate } from 'react-router-dom';

interface KOLProfilePageProps {
  kol: KOL;
  callHistory: Call[];
}

export function KOLProfilePage({ kol, callHistory }: KOLProfilePageProps) {
  const navigate = useNavigate();
  const wins = callHistory.filter(c => c.outcome === 'win').length;
  const completed = callHistory.filter(c => c.outcome !== 'pending').length;
  const profitable = wins;

  const avgReturn = callHistory
    .filter(c => c.outcome !== 'pending' && c.currentPrice)
    .reduce((acc, c) => acc + ((c.currentPrice! - c.priceAtCall) / c.priceAtCall * 100), 0) / completed || 0;

  const trackedSince = '2.3y';

  const tags = kol.id === 'willy-woo'
    ? ['On-chain analyst', 'BTC specialist']
    : kol.id === 'michael-saylor'
    ? ['Corporate treasury', 'BTC maximalist']
    : ['Market analyst'];

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
                    className="px-2 sm:px-3 py-1 bg-white/5 border border-white/10 rounded-lg text-xs text-white/80 backdrop-blur-sm"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          </div>

          <GlassCard className={`p-6 sm:p-8 text-center mb-6 sm:mb-8 ${
            kol.tier === 'good' ? 'bg-gradient-to-br from-green-500/10 to-emerald-500/10 border-green-500/30' :
            kol.tier === 'mixed' ? 'bg-gradient-to-br from-amber-500/10 to-orange-500/10 border-amber-500/30' :
            'bg-gradient-to-br from-red-500/10 to-rose-500/10 border-red-500/30'
          }`}>
            <div className={`text-5xl sm:text-6xl lg:text-7xl font-bold mb-2 ${
              kol.tier === 'good' ? 'text-green-400' :
              kol.tier === 'mixed' ? 'text-amber-400' :
              'text-red-400'
            }`}>
              {kol.reliabilityScore}%
            </div>
            <div className="text-xs sm:text-sm text-white/80 uppercase tracking-wide mb-1">Reliability Score</div>
            <div className="text-xs sm:text-sm text-white/60">
              {profitable} of {callHistory.length} calls profitable
            </div>
          </GlassCard>

          <div className="grid grid-cols-3 gap-3 sm:gap-4 lg:gap-6 mb-6 sm:mb-8">
            <div className="text-center">
              <div className="text-2xl sm:text-3xl font-bold text-white mb-1">{callHistory.length}</div>
              <div className="text-xs sm:text-sm text-white/60">Total calls</div>
            </div>
            <div className="text-center">
              <div className={`text-2xl sm:text-3xl font-bold mb-1 ${avgReturn >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {avgReturn >= 0 ? '+' : ''}{avgReturn.toFixed(0)}%
              </div>
              <div className="text-xs sm:text-sm text-white/60">Avg return</div>
            </div>
            <div className="text-center">
              <div className="text-2xl sm:text-3xl font-bold text-white mb-1">{trackedSince}</div>
              <div className="text-xs sm:text-sm text-white/60">Tracked since</div>
            </div>
          </div>
        </div>

        {kol.walletAddress && (
          <div className="mb-6 sm:mb-8">
            <h2 className="text-xs sm:text-sm font-semibold text-white/80 uppercase tracking-wide mb-3 sm:mb-4">
              On-Chain Verification
            </h2>
            <GlassCard className="p-4 sm:p-5 border-green-500/30 bg-gradient-to-r from-green-500/10 to-emerald-500/10">
              <div className="flex items-start gap-2 sm:gap-3 mb-3 sm:mb-4">
                <div className="w-2 h-2 rounded-full bg-green-400 mt-1 sm:mt-2 flex-shrink-0"></div>
                <div className="flex-1 min-w-0">
                  <div className="text-xs sm:text-sm font-semibold text-green-300 mb-2">
                    Wallet verified - High conviction
                  </div>
                  <div className="text-xs text-white/70 font-mono break-all mb-3 sm:mb-4">
                    {kol.walletAddress}
                  </div>
                  {kol.walletHoldings && kol.walletHoldings.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-3 sm:mb-4">
                      {kol.walletHoldings.map((holding) => (
                        <span
                          key={holding.symbol}
                          className="px-2 sm:px-3 py-1 sm:py-1.5 bg-white/10 border border-white/20 rounded-lg text-xs text-white backdrop-blur-sm"
                        >
                          <span className="font-semibold">{holding.amount} {holding.symbol}</span>
                          <span className="text-white/60 ml-1 sm:ml-2">{holding.value}</span>
                          <span className="hidden sm:inline text-white/60 ml-2">Held 18 months</span>
                        </span>
                      ))}
                    </div>
                  )}
                  {kol.arkhamLink && (
                    <a
                      href={kol.arkhamLink}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 text-xs sm:text-sm text-green-400 hover:text-green-300 font-medium transition-colors"
                    >
                      View on Arkham →
                    </a>
                  )}
                </div>
              </div>
            </GlassCard>
          </div>
        )}

        <div>
          <h2 className="text-xs sm:text-sm font-semibold text-white/80 uppercase tracking-wide mb-3 sm:mb-5">
            Call History
          </h2>
          <GlassCard>
            {callHistory.map((call, index) => {
              const returnPct = call.currentPrice
                ? ((call.currentPrice - call.priceAtCall) / call.priceAtCall * 100)
                : 0;

              return (
                <div
                  key={call.id}
                  className="p-3 sm:p-4 lg:p-5 border-b border-white/5 last:border-b-0 hover:bg-white/5 transition-all duration-300"
                >
                  <div className="flex flex-col sm:flex-row items-start gap-2 sm:gap-4">
                    <div className="flex-1 w-full sm:w-auto min-w-0">
                      <div className="flex flex-wrap items-center gap-2 sm:gap-3 mb-1 sm:mb-2">
                        <span className="text-xs sm:text-sm text-white/40">
                          {new Date(call.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                        </span>
                        <span className="px-2 py-0.5 bg-purple-500/20 border border-purple-500/30 rounded text-xs text-purple-300 font-medium">
                          {call.symbol}
                        </span>
                        <span className="text-xs sm:text-sm text-white">{call.snippet}</span>
                      </div>
                    </div>
                    {call.currentPrice && (
                      <div className={`text-xs sm:text-sm font-semibold flex-shrink-0 ${
                        returnPct >= 0 ? 'text-green-400' : 'text-red-400'
                      }`}>
                        {returnPct >= 0 ? '+' : ''}{returnPct.toFixed(1)}%
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
