import { TrendingUp, TrendingDown, AlertCircle, Activity, ArrowUpRight } from 'lucide-react';
import { Call, KOL, AssetData } from '../../types';
import { Avatar } from '../components/Avatar';
import { ScorePill } from '../components/ScorePill';
import { GlassCard } from '../components/GlassCard';
import { useNavigate } from 'react-router-dom';

interface DashboardPageProps {
  calls: Call[];
  kols: Record<string, KOL>;
  assets: Record<string, AssetData>;
}

export function DashboardPage({ calls, kols, assets }: DashboardPageProps) {
  const navigate = useNavigate();

  const recentCalls = [...calls]
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    .slice(0, 5);

  const topMovers = Object.values(assets)
    .sort((a, b) => Math.abs(b.change24h) - Math.abs(a.change24h))
    .slice(0, 4);

  const topKOLs = Object.values(kols)
    .sort((a, b) => b.reliabilityScore - a.reliabilityScore)
    .slice(0, 3);

  const rugAlerts = calls.filter(c => {
    const kol = kols[c.kolId];
    return kol && kol.tier === 'bad' && c.symbol === 'MOONX';
  });

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor(diff / (1000 * 60));

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  };

  const totalTracked = Object.keys(kols).length;
  const totalCalls = calls.length * 12;
  const avgAccuracy = 68;
  const activeAlerts = rugAlerts.length;

  return (
    <div className="min-h-screen text-white relative z-10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-10">
        <div className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold mb-2 bg-gradient-to-r from-white to-purple-200 bg-clip-text text-transparent">
            Dashboard
          </h1>
          <p className="text-sm sm:text-base text-white/60">Your command center for tracking KOL calls and market sentiment</p>
        </div>

        {/* Stats Overview */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-6 sm:mb-8">
          <GlassCard className="p-4 sm:p-6">
            <div className="flex items-center justify-between mb-2 sm:mb-3">
              <div className="text-xs sm:text-sm text-white/60">KOLs Tracked</div>
              <Activity className="w-4 h-4 sm:w-5 sm:h-5 text-purple-400" />
            </div>
            <div className="text-2xl sm:text-3xl font-bold bg-gradient-to-r from-white to-purple-200 bg-clip-text text-transparent">
              {totalTracked}
            </div>
            <div className="text-xs text-white/40 mt-1">Across all platforms</div>
          </GlassCard>

          <GlassCard className="p-4 sm:p-6">
            <div className="flex items-center justify-between mb-2 sm:mb-3">
              <div className="text-xs sm:text-sm text-white/60">Calls Verified</div>
              <TrendingUp className="w-4 h-4 sm:w-5 sm:h-5 text-green-400" />
            </div>
            <div className="text-2xl sm:text-3xl font-bold bg-gradient-to-r from-white to-blue-200 bg-clip-text text-transparent">
              {(totalCalls / 1000).toFixed(1)}k
            </div>
            <div className="text-xs text-white/40 mt-1">Last 30 days</div>
          </GlassCard>

          <GlassCard className="p-4 sm:p-6">
            <div className="flex items-center justify-between mb-2 sm:mb-3">
              <div className="text-xs sm:text-sm text-white/60">Avg Accuracy</div>
              <div className="w-4 h-4 sm:w-5 sm:h-5 rounded-full bg-green-500/20 flex items-center justify-center">
                <div className="w-2 h-2 rounded-full bg-green-400"></div>
              </div>
            </div>
            <div className="text-2xl sm:text-3xl font-bold bg-gradient-to-r from-white to-violet-200 bg-clip-text text-transparent">
              {avgAccuracy}%
            </div>
            <div className="text-xs text-white/40 mt-1">Community wide</div>
          </GlassCard>

          <GlassCard className="p-4 sm:p-6 border-red-500/30 bg-gradient-to-r from-red-500/10 to-orange-500/10">
            <div className="flex items-center justify-between mb-2 sm:mb-3">
              <div className="text-xs sm:text-sm text-red-300">Active Alerts</div>
              <AlertCircle className="w-4 h-4 sm:w-5 sm:h-5 text-red-400" />
            </div>
            <div className="text-2xl sm:text-3xl font-bold text-red-400">
              {activeAlerts}
            </div>
            <div className="text-xs text-red-300/60 mt-1">Requires attention</div>
          </GlassCard>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6 mb-6 sm:mb-8">
          {/* Recent Activity */}
          <div className="lg:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-white/80 uppercase tracking-wide">
                Recent Activity
              </h2>
              <button
                onClick={() => navigate('/live')}
                className="text-sm text-purple-400 hover:text-purple-300 font-medium transition-colors flex items-center gap-1"
              >
                View all
                <ArrowUpRight className="w-4 h-4" />
              </button>
            </div>
            <GlassCard>
              {recentCalls.map((call) => {
                const kol = kols[call.kolId];
                if (!kol) return null;

                return (
                  <div
                    key={call.id}
                    className="p-4 border-b border-white/5 last:border-b-0 hover:bg-white/5 cursor-pointer transition-all duration-300"
                    onClick={() => navigate(`/kol/${kol.id}`)}
                  >
                    <div className="flex items-start gap-3">
                      <Avatar initials={kol.initials} size="sm" tier={kol.tier} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-semibold text-white text-sm">{kol.name}</span>
                          <span className="text-xs text-white/40">{formatTimestamp(call.timestamp)}</span>
                        </div>
                        <p className="text-xs text-white/70 mb-2">{call.snippet}</p>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/market/${call.symbol}`);
                            }}
                            className="px-2 py-0.5 bg-purple-500/20 border border-purple-500/30 rounded text-xs text-purple-300 font-medium hover:bg-purple-500/30 transition-colors"
                          >
                            {call.symbol}
                          </button>
                          <ScorePill score={kol.reliabilityScore} tier={kol.tier} size="sm" />
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </GlassCard>
          </div>

          {/* Top Reliable KOLs */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-white/80 uppercase tracking-wide">
                Top Reliable
              </h2>
              <button
                onClick={() => navigate('/kols')}
                className="text-sm text-purple-400 hover:text-purple-300 font-medium transition-colors flex items-center gap-1"
              >
                View all
                <ArrowUpRight className="w-4 h-4" />
              </button>
            </div>
            <GlassCard>
              {topKOLs.map((kol) => (
                <div
                  key={kol.id}
                  className="p-4 border-b border-white/5 last:border-b-0 hover:bg-white/5 cursor-pointer transition-all duration-300"
                  onClick={() => navigate(`/kol/${kol.id}`)}
                >
                  <div className="flex items-center gap-3">
                    <Avatar initials={kol.initials} size="sm" tier={kol.tier} />
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-white text-sm mb-0.5">{kol.name}</div>
                      <div className="text-xs text-white/40">{kol.primaryAsset}</div>
                    </div>
                    <ScorePill score={kol.reliabilityScore} tier={kol.tier} size="sm" />
                  </div>
                </div>
              ))}
            </GlassCard>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
          {/* Top Movers */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-white/80 uppercase tracking-wide">
                Top Movers (24h)
              </h2>
              <button
                onClick={() => navigate('/markets')}
                className="text-sm text-purple-400 hover:text-purple-300 font-medium transition-colors flex items-center gap-1"
              >
                View all
                <ArrowUpRight className="w-4 h-4" />
              </button>
            </div>
            <GlassCard>
              {topMovers.map((asset) => {
                const isPositive = asset.change24h > 0;
                return (
                  <div
                    key={asset.symbol}
                    className="p-4 border-b border-white/5 last:border-b-0 hover:bg-white/5 cursor-pointer transition-all duration-300"
                    onClick={() => navigate(`/market/${asset.symbol}`)}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-violet-600 flex items-center justify-center text-white font-bold text-sm shadow-lg shadow-purple-500/50">
                        {asset.symbol.substring(0, 3)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-semibold text-white text-sm mb-0.5">{asset.name}</div>
                        <div className="text-xs text-white/40">${asset.price.toLocaleString()}</div>
                      </div>
                      <div className={`flex items-center gap-1 text-sm font-semibold ${
                        isPositive ? 'text-green-400' : 'text-red-400'
                      }`}>
                        {isPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                        {isPositive ? '+' : ''}{asset.change24h}%
                      </div>
                    </div>
                  </div>
                );
              })}
            </GlassCard>
          </div>

          {/* Alerts */}
          {rugAlerts.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold text-red-300 uppercase tracking-wide flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-red-400 animate-pulse"></div>
                  Rug Alerts
                </h2>
                <span className="text-xs text-white/40 uppercase tracking-wide">Last 24h</span>
              </div>
              <GlassCard className="border-red-500/30 bg-gradient-to-r from-red-500/10 to-pink-500/10">
                {rugAlerts.map((call) => {
                  const kol = kols[call.kolId];
                  if (!kol) return null;

                  return (
                    <div
                      key={call.id}
                      className="p-4 border-b border-white/5 last:border-b-0 hover:bg-white/5 cursor-pointer transition-all duration-300"
                      onClick={() => navigate(`/market/${call.symbol}`)}
                    >
                      <div className="flex items-start gap-3">
                        <div className="w-8 h-8 rounded-full bg-red-500/20 flex items-center justify-center flex-shrink-0 border border-red-500/30">
                          <AlertCircle className="w-4 h-4 text-red-400" />
                        </div>
                        <div className="flex-1">
                          <p className="text-sm text-white/90 mb-1">
                            <span className="font-semibold text-white">{call.symbol}</span> flagged as honeypot
                          </p>
                          <p className="text-xs text-white/60">
                            Called by {kol.name} ({kol.reliabilityScore}% reliability)
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </GlassCard>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
