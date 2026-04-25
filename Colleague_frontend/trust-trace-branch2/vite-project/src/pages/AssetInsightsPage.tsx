import { ArrowLeft, TrendingUp, Circle, User, Wallet, ChevronLeft, ChevronRight } from 'lucide-react';
import { useState } from 'react';
import { AssetData, KOL } from '../../types';
import { GlassCard } from '../components/GlassCard';
import { Avatar } from '../components/Avatar';
import { ScorePill } from '../components/ScorePill';
import { Button } from '../components/ui/button';
import { useNavigate } from 'react-router-dom';

interface AssetInsightsPageProps {
  asset: AssetData;
}

interface Insight {
  icon: any;
  iconColor: string;
  iconBg: string;
  label: string;
  value: string;
  status: 'positive' | 'neutral' | 'negative';
}

export function AssetInsightsPage({ asset }: AssetInsightsPageProps) {
  const navigate = useNavigate();
  const [insightsExpanded, setInsightsExpanded] = useState(true);
  const isPositive = asset.change24h > 0;

  const chartPeriods = ['24h', '7d', '30d', '90d', '1y'];
  const selectedPeriod = '30d';

  const dominance = asset.symbol === 'BTC' ? '58.2%' : undefined;

  const kolsCalling: Array<{
    name: string;
    handle: string;
    initials: string;
    call: string;
    timestamp: string;
    score: number;
    tier: 'good' | 'mixed' | 'bad';
    id: string;
  }> = asset.symbol === 'BTC' ? [
    { name: 'Willy Woo', handle: '@woonomic', initials: 'WW', call: 'Bullish', timestamp: '5 min ago', score: 81, tier: 'good', id: 'willy-woo' },
    { name: 'Michael Saylor', handle: '@saylor', initials: 'MS', call: 'Bullish', timestamp: '4h ago', score: 87, tier: 'good', id: 'michael-saylor' },
  ] : [];

  const insights: Insight[] = [
    {
      icon: TrendingUp,
      iconColor: 'text-green-400',
      iconBg: 'bg-green-500/20',
      label: 'Trend',
      value: isPositive ? 'Slowly rising' : 'Declining',
      status: isPositive ? 'positive' : 'negative',
    },
    {
      icon: Circle,
      iconColor: 'text-green-400',
      iconBg: 'bg-green-500/20',
      label: 'Volume',
      value: 'Above 30-day average',
      status: 'positive',
    },
    {
      icon: User,
      iconColor: 'text-amber-400',
      iconBg: 'bg-amber-500/20',
      label: asset.symbol === 'BTC' ? 'Willy Woo on BTC' : 'KOL Sentiment',
      value: asset.symbol === 'BTC' ? 'Strong track record - 81% accuracy' : 'Mixed track record - 72% accuracy',
      status: 'neutral',
    },
    {
      icon: Wallet,
      iconColor: kolsCalling.length > 0 ? 'text-green-400' : 'text-red-400',
      iconBg: kolsCalling.length > 0 ? 'bg-green-500/20' : 'bg-red-500/20',
      label: 'Wallet check',
      value: kolsCalling.length > 0 ? 'On-chain holdings verified' : 'No on-chain holdings verified',
      status: kolsCalling.length > 0 ? 'positive' : 'negative',
    },
  ];

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
            <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-gradient-to-br from-purple-500 to-violet-600 flex items-center justify-center text-white font-bold text-base sm:text-lg shadow-lg shadow-purple-500/50">
              {asset.symbol.substring(0, 3)}
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-bold text-white">{asset.name}</h1>
              <div className="text-xs sm:text-sm text-white/60">{asset.symbol}, USD</div>
            </div>
          </div>

          <div className="mb-4 sm:mb-6">
            <div className="flex flex-wrap items-baseline gap-2 sm:gap-3 mb-2">
              <span className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white">
                ${asset.price.toLocaleString()}
              </span>
              <span className={`text-lg sm:text-xl font-semibold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                {isPositive ? '+' : ''}{asset.change24h}%
              </span>
              <span className="text-xs sm:text-sm text-white/60">{selectedPeriod}</span>
            </div>
          </div>

          <div className="flex flex-wrap gap-1.5 sm:gap-2 mb-4 sm:mb-6">
            {chartPeriods.map((period) => (
              <button
                key={period}
                className={`px-3 sm:px-4 py-1 sm:py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all ${
                  period === selectedPeriod
                    ? 'bg-white/10 text-white border border-white/20'
                    : 'text-white/60 hover:text-white hover:bg-white/5'
                }`}
              >
                {period}
              </button>
            ))}
          </div>

          <div className="flex flex-col lg:flex-row gap-3 sm:gap-4 mb-4 sm:mb-6">
            <div className="flex-1 h-48 sm:h-56 lg:h-48 bg-gradient-to-br from-green-500/5 to-emerald-500/5 rounded-xl border border-green-500/20 relative overflow-hidden">
              <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 100 100">
                <defs>
                  <linearGradient id="chartGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" stopColor="rgb(34, 197, 94)" stopOpacity="0.3" />
                    <stop offset="100%" stopColor="rgb(34, 197, 94)" stopOpacity="0.05" />
                  </linearGradient>
                </defs>
                <path
                  d="M 0,60 L 20,55 L 40,50 L 60,45 L 80,35 L 100,30 L 100,100 L 0,100 Z"
                  fill="url(#chartGradient)"
                />
                <path
                  d="M 0,60 L 20,55 L 40,50 L 60,45 L 80,35 L 100,30"
                  fill="none"
                  stroke="rgb(34, 197, 94)"
                  strokeWidth="0.5"
                />
              </svg>
            </div>

            <div className={`transition-all duration-300 ${insightsExpanded ? 'w-full lg:w-64' : 'w-14'}`}>
              <GlassCard className="h-full p-3 relative">
                <button
                  onClick={() => setInsightsExpanded(!insightsExpanded)}
                  className="absolute -left-3 lg:-left-3 top-1/2 lg:top-1/2 -translate-y-1/2 w-6 h-6 bg-white/10 border border-white/20 rounded-full flex items-center justify-center hover:bg-white/20 transition-all backdrop-blur-sm z-10"
                >
                  {insightsExpanded ? (
                    <ChevronRight className="w-3 h-3 text-white" />
                  ) : (
                    <ChevronLeft className="w-3 h-3 text-white" />
                  )}
                </button>

                <div className={`space-y-3 ${insightsExpanded ? '' : 'flex flex-row lg:flex-col gap-3 justify-center'}`}>
                  {insights.map((insight, index) => {
                    const Icon = insight.icon;
                    return (
                      <div
                        key={index}
                        className={`transition-all duration-300 ${
                          insightsExpanded ? 'opacity-100' : 'opacity-100'
                        }`}
                      >
                        {insightsExpanded ? (
                          <div className="flex items-start gap-2">
                            <div className={`w-6 h-6 sm:w-7 sm:h-7 rounded-full ${insight.iconBg} flex items-center justify-center flex-shrink-0`}>
                              <Icon className={`w-3 h-3 sm:w-3.5 sm:h-3.5 ${insight.iconColor}`} />
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="text-xs text-white/60 mb-0.5">{insight.label}</div>
                              <div className="text-xs font-medium text-white leading-tight">{insight.value}</div>
                            </div>
                          </div>
                        ) : (
                          <div className="flex justify-center">
                            <div className={`w-7 h-7 sm:w-8 sm:h-8 rounded-full ${insight.iconBg} flex items-center justify-center`}>
                              <Icon className={`w-3.5 h-3.5 sm:w-4 sm:h-4 ${insight.iconColor}`} />
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </GlassCard>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-x-4 sm:gap-x-8 lg:gap-x-12 gap-y-3 sm:gap-y-4">
            <div>
              <div className="text-xs sm:text-sm text-white/60 mb-1">24h volume</div>
              <div className="text-lg sm:text-xl lg:text-2xl font-bold text-white">{asset.volume24h}</div>
            </div>
            <div>
              <div className="text-xs sm:text-sm text-white/60 mb-1">Market cap</div>
              <div className="text-lg sm:text-xl lg:text-2xl font-bold text-white">{asset.marketCap}</div>
            </div>
            {asset.holders && (
              <div>
                <div className="text-xs sm:text-sm text-white/60 mb-1">Holders</div>
                <div className="text-lg sm:text-xl lg:text-2xl font-bold text-white">{(asset.holders / 1000000).toFixed(1)}M</div>
              </div>
            )}
            {dominance && (
              <div>
                <div className="text-xs sm:text-sm text-white/60 mb-1">Dominance</div>
                <div className="text-lg sm:text-xl lg:text-2xl font-bold text-white">{dominance}</div>
              </div>
            )}
          </div>
        </GlassCard>

        <GlassCard className="p-4 sm:p-5 lg:p-6 mb-4 sm:mb-6 bg-gradient-to-br from-green-500/10 to-emerald-500/10 border-green-500/30">
          <div className="mb-2 sm:mb-3">
            <h2 className="text-xs font-semibold text-green-300 uppercase tracking-wide">
              AI Market Analysis
            </h2>
          </div>
          <h3 className="text-base sm:text-lg font-semibold text-white mb-2 sm:mb-3">Momentum looks strong</h3>
          <p className="text-xs sm:text-sm text-white/80 leading-relaxed">
            {asset.symbol} is up {Math.abs(asset.change24h)}% over the past 30 days with rising volume. On-chain data shows long-term holders
            accumulating. Multiple high-accuracy KOLs are bullish. Use this data to form your own bias — not as
            financial advice.
          </p>
        </GlassCard>

        {kolsCalling.length > 0 && (
          <div>
            <h2 className="text-xs sm:text-sm font-semibold text-white/80 uppercase tracking-wide mb-3 sm:mb-5">
              Who's Calling This Asset
            </h2>
            <GlassCard>
              {kolsCalling.map((kol, index) => (
                <div
                  key={index}
                  className="p-3 sm:p-4 lg:p-5 border-b border-white/5 last:border-b-0 hover:bg-white/5 cursor-pointer transition-all duration-300"
                  onClick={() => navigate(`/kol/${kol.id}`)}
                >
                  <div className="flex items-center gap-3 sm:gap-4">
                    <Avatar initials={kol.initials} size="md" tier={kol.tier} />
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-sm sm:text-base text-white mb-0.5">{kol.name}</div>
                      <div className="text-xs sm:text-sm text-white/60">
                        {kol.call} · {kol.timestamp}
                      </div>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <ScorePill score={kol.score} tier={kol.tier} size="sm" />
                    </div>
                  </div>
                </div>
              ))}
            </GlassCard>
          </div>
        )}
      </div>
    </div>
  );
}
