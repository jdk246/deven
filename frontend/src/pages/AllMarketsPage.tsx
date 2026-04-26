import { Search, SlidersHorizontal, TrendingDown, TrendingUp, X } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { GlassCard } from "../components/GlassCard";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import type { AssetData } from "../types";

interface AllMarketsPageProps {
  assets: Record<string, AssetData>;
}

type RiskFilter = "all" | "low" | "medium" | "high" | "unrated";
type AttentionFilter = "all" | "strong" | "watchlist" | "emerging" | "unscored";
type SortOption =
  | "attention_desc"
  | "market_cap_desc"
  | "volume_desc"
  | "change_desc"
  | "change_asc"
  | "name_asc";

function compareNullableNumber(left: number | null | undefined, right: number | null | undefined) {
  return (right ?? Number.NEGATIVE_INFINITY) - (left ?? Number.NEGATIVE_INFINITY);
}

export function AllMarketsPage({ assets }: AllMarketsPageProps) {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const [chainFilter, setChainFilter] = useState("all");
  const [riskFilter, setRiskFilter] = useState<RiskFilter>("all");
  const [attentionFilter, setAttentionFilter] = useState<AttentionFilter>("all");
  const [sortBy, setSortBy] = useState<SortOption>("attention_desc");

  const allAssets = useMemo(() => Object.values(assets), [assets]);

  const availableChains = useMemo(
    () =>
      Array.from(
        new Map(
          allAssets.map((asset) => [
            asset.chainId,
            {
              chainId: asset.chainId,
              chainName: asset.chainName,
              chainShortName: asset.chainShortName,
            },
          ]),
        ).values(),
      ).sort((left, right) => left.chainName.localeCompare(right.chainName)),
    [allAssets],
  );

  const filteredAssets = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();

    const matchesAttentionFilter = (asset: AssetData) => {
      const score = asset.attentionScore;

      switch (attentionFilter) {
        case "strong":
          return score !== null && score !== undefined && score >= 70;
        case "watchlist":
          return score !== null && score !== undefined && score >= 50 && score < 70;
        case "emerging":
          return score !== null && score !== undefined && score < 50;
        case "unscored":
          return score === null || score === undefined;
        default:
          return true;
      }
    };

    const matchesRiskFilter = (asset: AssetData) => {
      if (riskFilter === "all") {
        return true;
      }
      if (riskFilter === "unrated") {
        return !asset.riskLevel;
      }
      return asset.riskLevel === riskFilter;
    };

    const items = allAssets.filter((asset) => {
      const matchesQuery =
        query.length === 0 ||
        asset.name.toLowerCase().includes(query) ||
        asset.symbol.toLowerCase().includes(query) ||
        asset.chainName.toLowerCase().includes(query);
      const matchesChain = chainFilter === "all" || asset.chainId === chainFilter;

      return (
        matchesQuery &&
        matchesChain &&
        matchesRiskFilter(asset) &&
        matchesAttentionFilter(asset)
      );
    });

    items.sort((left, right) => {
      switch (sortBy) {
        case "market_cap_desc":
          return (
            compareNullableNumber(left.marketCapValue, right.marketCapValue) ||
            compareNullableNumber(left.attentionScore, right.attentionScore)
          );
        case "volume_desc":
          return (
            compareNullableNumber(left.volume24hValue, right.volume24hValue) ||
            compareNullableNumber(left.attentionScore, right.attentionScore)
          );
        case "change_desc":
          return (
            compareNullableNumber(left.change24h, right.change24h) ||
            compareNullableNumber(left.attentionScore, right.attentionScore)
          );
        case "change_asc":
          return (
            compareNullableNumber(right.change24h, left.change24h) ||
            compareNullableNumber(left.attentionScore, right.attentionScore)
          );
        case "name_asc":
          return (
            left.name.localeCompare(right.name) ||
            left.symbol.localeCompare(right.symbol)
          );
        case "attention_desc":
        default:
          return (
            compareNullableNumber(left.attentionScore, right.attentionScore) ||
            compareNullableNumber(left.marketCapValue, right.marketCapValue)
          );
      }
    });

    return items;
  }, [allAssets, attentionFilter, chainFilter, riskFilter, searchQuery, sortBy]);

  const activeFilterCount = useMemo(
    () =>
      [
        searchQuery.trim().length > 0,
        chainFilter !== "all",
        riskFilter !== "all",
        attentionFilter !== "all",
        sortBy !== "attention_desc",
      ].filter(Boolean).length,
    [attentionFilter, chainFilter, riskFilter, searchQuery, sortBy],
  );

  const clearFilters = () => {
    setSearchQuery("");
    setChainFilter("all");
    setRiskFilter("all");
    setAttentionFilter("all");
    setSortBy("attention_desc");
  };

  return (
    <div className="min-h-screen text-white relative z-10">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-10">
        <div className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold mb-3 bg-gradient-to-r from-white to-purple-200 bg-clip-text text-transparent">
            Markets
          </h1>
          <p className="text-sm sm:text-base text-white/60">
            Showing {filteredAssets.length} of {allAssets.length} tracked tokens
          </p>
        </div>

        <GlassCard className="p-3 sm:p-4 mb-6 sm:mb-8">
          <div className="flex items-center justify-between gap-3 mb-3">
            <div className="flex items-center gap-2 text-sm text-white/70">
              <SlidersHorizontal className="w-4 h-4 text-purple-200" />
              <span>Filter markets</span>
            </div>
            {activeFilterCount > 0 ? (
              <Button
                variant="ghost"
                size="sm"
                className="text-white/70 hover:text-white hover:bg-white/5"
                onClick={clearFilters}
              >
                <X className="w-4 h-4" />
                Clear filters
              </Button>
            ) : null}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40 w-4 h-4 sm:w-5 sm:h-5" />
              <Input
                placeholder="Search assets by name, symbol, or chain..."
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                className="pl-9 sm:pl-10 text-sm sm:text-base bg-black/20 border-white/10 text-white placeholder:text-white/40 backdrop-blur-sm"
              />
            </div>

            <Select value={sortBy} onValueChange={(value) => setSortBy(value as SortOption)}>
              <SelectTrigger className="bg-black/20 border-white/10 text-white">
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent className="bg-[#120f1d] border-white/10 text-white">
                <SelectItem value="attention_desc">Sort: Attention score</SelectItem>
                <SelectItem value="market_cap_desc">Sort: Market cap</SelectItem>
                <SelectItem value="volume_desc">Sort: 24h volume</SelectItem>
                <SelectItem value="change_desc">Sort: 24h gainers</SelectItem>
                <SelectItem value="change_asc">Sort: 24h losers</SelectItem>
                <SelectItem value="name_asc">Sort: Name A-Z</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <Select value={chainFilter} onValueChange={setChainFilter}>
              <SelectTrigger className="bg-black/20 border-white/10 text-white">
                <SelectValue placeholder="All chains" />
              </SelectTrigger>
              <SelectContent className="bg-[#120f1d] border-white/10 text-white">
                <SelectItem value="all">All chains</SelectItem>
                {availableChains.map((chain) => (
                  <SelectItem key={chain.chainId} value={chain.chainId}>
                    {chain.chainName}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={riskFilter} onValueChange={(value) => setRiskFilter(value as RiskFilter)}>
              <SelectTrigger className="bg-black/20 border-white/10 text-white">
                <SelectValue placeholder="All risk levels" />
              </SelectTrigger>
              <SelectContent className="bg-[#120f1d] border-white/10 text-white">
                <SelectItem value="all">All risk levels</SelectItem>
                <SelectItem value="low">Low risk</SelectItem>
                <SelectItem value="medium">Medium risk</SelectItem>
                <SelectItem value="high">High risk</SelectItem>
                <SelectItem value="unrated">Unrated</SelectItem>
              </SelectContent>
            </Select>

            <Select
              value={attentionFilter}
              onValueChange={(value) => setAttentionFilter(value as AttentionFilter)}
            >
              <SelectTrigger className="bg-black/20 border-white/10 text-white">
                <SelectValue placeholder="All attention bands" />
              </SelectTrigger>
              <SelectContent className="bg-[#120f1d] border-white/10 text-white">
                <SelectItem value="all">All attention bands</SelectItem>
                <SelectItem value="strong">Strong attention (70+)</SelectItem>
                <SelectItem value="watchlist">Watchlist range (50-69)</SelectItem>
                <SelectItem value="emerging">Emerging (&lt;50)</SelectItem>
                <SelectItem value="unscored">Unscored</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="mt-3 text-xs text-white/45">
            Use filters to narrow by chain, audit risk, or attention band while keeping the same tracked universe.
          </div>
        </GlassCard>

        <GlassCard>
          <div className="hidden md:block p-3 sm:p-4 border-b border-white/5">
            <div className="grid grid-cols-12 gap-3 sm:gap-4 text-xs text-white/40 uppercase tracking-wide">
              <div className="col-span-1">#</div>
              <div className="col-span-4">Asset</div>
              <div className="col-span-2 text-right">Price</div>
              <div className="col-span-2 text-right">24h %</div>
              <div className="col-span-1 text-right">Score</div>
              <div className="col-span-2 text-right">Market Cap</div>
            </div>
          </div>
          {filteredAssets.map((asset, index) => {
            const isPositive = (asset.change24h ?? 0) > 0;
            return (
              <div
                key={asset.key}
                className="p-3 sm:p-4 border-b border-white/5 last:border-b-0 hover:bg-white/5 cursor-pointer transition-all duration-300"
                onClick={() =>
                  navigate(
                    `/market/${encodeURIComponent(asset.chainId)}/${encodeURIComponent(asset.contractAddress)}`,
                  )
                }
              >
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
                      <div className="text-xs text-white/40">
                        {asset.symbol} - {asset.chainShortName}
                      </div>
                    </div>
                  </div>
                  <div className="col-span-2 text-right font-semibold text-sm sm:text-base text-white">
                    {asset.price !== null && asset.price !== undefined
                      ? `$${asset.price.toLocaleString()}`
                      : "N/A"}
                  </div>
                  <div
                    className={`col-span-2 text-right font-semibold flex items-center justify-end gap-1 text-sm sm:text-base ${
                      isPositive ? "text-green-400" : "text-red-400"
                    }`}
                  >
                    {isPositive ? (
                      <TrendingUp className="w-3 h-3 sm:w-4 sm:h-4" />
                    ) : (
                      <TrendingDown className="w-3 h-3 sm:w-4 sm:h-4" />
                    )}
                    {asset.change24h !== null && asset.change24h !== undefined ? (
                      <>
                        {isPositive ? "+" : ""}
                        {asset.change24h.toFixed(2)}%
                      </>
                    ) : (
                      "N/A"
                    )}
                  </div>
                  <div className="col-span-1 text-right text-sm sm:text-base text-white/80">
                    {asset.attentionScore !== null && asset.attentionScore !== undefined
                      ? asset.attentionScore.toFixed(0)
                      : "-"}
                  </div>
                  <div className="col-span-2 text-right text-sm sm:text-base text-white/60">
                    {asset.marketCap}
                  </div>
                </div>

                <div className="md:hidden flex items-center gap-3">
                  <div className="text-white/40 font-medium text-xs">{index + 1}</div>
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-violet-600 flex items-center justify-center text-white text-sm font-bold shadow-lg shadow-purple-500/50">
                    {asset.symbol.substring(0, 3)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-sm text-white">{asset.name}</div>
                    <div className="text-xs text-white/40">
                      {asset.symbol} - {asset.chainShortName} - Attention{" "}
                      {asset.attentionScore?.toFixed(0) ?? "-"}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-semibold text-sm text-white">
                      {asset.price !== null && asset.price !== undefined
                        ? `$${asset.price.toLocaleString()}`
                        : "N/A"}
                    </div>
                    <div
                      className={`text-xs font-semibold flex items-center justify-end gap-1 ${
                        isPositive ? "text-green-400" : "text-red-400"
                      }`}
                    >
                      {isPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                      {asset.change24h !== null && asset.change24h !== undefined ? (
                        <>
                          {isPositive ? "+" : ""}
                          {asset.change24h.toFixed(2)}%
                        </>
                      ) : (
                        "N/A"
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
          {filteredAssets.length === 0 ? (
            <div className="p-8 sm:p-10 text-center">
              <div className="text-white font-medium mb-2">No markets match those filters</div>
              <p className="text-sm text-white/50 mb-4">
                Try widening the chain or attention filters, or clear the search query.
              </p>
              <Button
                variant="outline"
                className="border-white/10 bg-white/5 text-white hover:bg-white/10"
                onClick={clearFilters}
              >
                Reset markets view
              </Button>
            </div>
          ) : null}
        </GlassCard>
      </div>
    </div>
  );
}
