import { Search, TrendingUp, TrendingDown } from 'lucide-react';
import { useState } from 'react';
import { AssetData } from '../../types';
import { GlassCard } from '../components/GlassCard';
import { Input } from '../components/ui/input';
import { useNavigate } from 'react-router-dom';

interface AllMarketsPageProps {
  assets: Record<string, AssetData>;
}

export function AllMarketsPage({ assets }: AllMarketsPageProps) {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');

  const sortedAssets = Object.values(assets)
    .sort((a, b) => {
      const parseMarketCap = (str: string) => {
        const num = parseFloat(str.replace(/[$TBMKk]/g, ''));
        if (str.includes('T')) return num * 1000000000000;
        if (str.includes('B')) return num * 1000000000;
        if (str.includes('M')) return num * 1000000;
        if (str.includes('K') || str.includes('k')) return num * 1000;
        return num;
      };
      return parseMarketCap(b.marketCap) - parseMarketCap(a.marketCap);
    });

  const filteredAssets = sortedAssets.filter(asset =>
    asset.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    asset.symbol.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="min-h-screen text-white relative z-10">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-10">
        <div className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold mb-3 bg-gradient-to-r from-white to-purple-200 bg-clip-text text-transparent">
            Markets
          </h1>
          <p className="text-sm sm:text-base text-white/60">
            Track prices and KOL sentiment across {sortedAssets.length} crypto assets
          </p>
        </div>

        <GlassCard className="p-3 sm:p-4 mb-6 sm:mb-8">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40 w-4 h-4 sm:w-5 sm:h-5" />
            <Input
              placeholder="Search assets by name or symbol..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 sm:pl-10 text-sm sm:text-base bg-black/20 border-white/10 text-white placeholder:text-white/40 backdrop-blur-sm"
            />
          </div>
        </GlassCard>

        <GlassCard>
          <div className="hidden md:block p-3 sm:p-4 border-b border-white/5">
            <div className="grid grid-cols-12 gap-3 sm:gap-4 text-xs text-white/40 uppercase tracking-wide">
              <div className="col-span-1">#</div>
              <div className="col-span-4">Asset</div>
              <div className="col-span-2 text-right">Price</div>
              <div className="col-span-2 text-right">24h %</div>
              <div className="col-span-3 text-right">Market Cap</div>
            </div>
          </div>
          {filteredAssets.map((asset, index) => {
            const isPositive = asset.change24h > 0;
            return (
              <div
                key={asset.symbol}
                className="p-3 sm:p-4 border-b border-white/5 last:border-b-0 hover:bg-white/5 cursor-pointer transition-all duration-300"
                onClick={() => navigate(`/market/${asset.symbol}`)}
              >
                {/* Desktop Layout */}
                <div className="hidden md:grid grid-cols-12 gap-3 sm:gap-4 items-center">
                  <div className="col-span-1 text-white/40 font-medium text-xs sm:text-sm">
                    {index + 1}
                  </div>
                  <div className="col-span-4 flex items-center gap-2 sm:gap-3">
                    <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-gradient-to-br from-purple-500 to-violet-600 flex items-center justify-center text-white text-xs sm:text-sm font-bold shadow-lg shadow-purple-500/50">
                      {asset.symbol.substring(0, 3)}
                    </div>
                    <div>
                      <div className="font-semibold text-sm sm:text-base text-white">{asset.name}</div>
                      <div className="text-xs text-white/40">{asset.symbol}</div>
                    </div>
                  </div>
                  <div className="col-span-2 text-right font-semibold text-sm sm:text-base text-white">
                    ${asset.price.toLocaleString()}
                  </div>
                  <div className={`col-span-2 text-right font-semibold flex items-center justify-end gap-1 text-sm sm:text-base ${
                    isPositive ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {isPositive ? <TrendingUp className="w-3 h-3 sm:w-4 sm:h-4" /> : <TrendingDown className="w-3 h-3 sm:w-4 sm:h-4" />}
                    {isPositive ? '+' : ''}{asset.change24h}%
                  </div>
                  <div className="col-span-3 text-right text-sm sm:text-base text-white/60">
                    {asset.marketCap}
                  </div>
                </div>
                {/* Mobile Layout */}
                <div className="md:hidden flex items-center gap-3">
                  <div className="text-white/40 font-medium text-xs">
                    {index + 1}
                  </div>
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-violet-600 flex items-center justify-center text-white text-sm font-bold shadow-lg shadow-purple-500/50">
                    {asset.symbol.substring(0, 3)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-sm text-white">{asset.name}</div>
                    <div className="text-xs text-white/40">{asset.symbol}</div>
                  </div>
                  <div className="text-right">
                    <div className="font-semibold text-sm text-white">
                      ${asset.price.toLocaleString()}
                    </div>
                    <div className={`text-xs font-semibold flex items-center justify-end gap-1 ${
                      isPositive ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {isPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                      {isPositive ? '+' : ''}{asset.change24h}%
                    </div>
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
