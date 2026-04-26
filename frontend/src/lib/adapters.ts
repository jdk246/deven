import type {
  AgentHealthResponse,
  ChainOptionResponse,
  InsightItemResponse,
  KOLDetailResponse,
  KOLFeedItemResponse,
  KOLListItemResponse,
  KOLListResponse,
  KOLRankingItemResponse,
  KOLRankingsResponse,
  KOLTrackRecordCallResponse,
  KOLTrackRecordResponse,
  TokenDetailResponse,
  TokenListItemResponse,
  TokenListResponse,
  TrendingTokenResponse,
  ValidationResponse,
} from "../api/trustTrace";
import type {
  ActiveAlert,
  AppSnapshot,
  AssetData,
  AuditCheck,
  AuditRiskLevel,
  Call,
  ChainInfo,
  KOL,
  KOLDetailView,
  KOLMentionView,
  KOLPostView,
  MarketDetailView,
  ReliabilityTier,
  SignalType,
  SmartMoneySignalView,
  TokenAuditResult,
  ValidationCheckView,
} from "../types";

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function titleCase(value: string) {
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function safeName(name: string | null | undefined, fallback: string) {
  const trimmed = name?.trim();
  return trimmed || fallback;
}

const DEMO_KOL_ALIASES: Record<
  string,
  {
    displayName: string;
    uiHandle: string;
  }
> = {
  macro_mina: { displayName: "Raoul Pal", uiHandle: "@raoul_pal" },
  raoul_pal_demo: { displayName: "Raoul Pal", uiHandle: "@raoul_pal" },
  onchain_omar: { displayName: "Willy Woo", uiHandle: "@willy_woo" },
  willy_woo_demo: { displayName: "Willy Woo", uiHandle: "@willy_woo" },
  sol_sage: { displayName: "Ansem", uiHandle: "@ansem" },
  ansem_demo: { displayName: "Ansem", uiHandle: "@ansem" },
  bsc_bella: { displayName: "Crypto Kaleo", uiHandle: "@crypto_kaleo" },
  crypto_kaleo_demo: { displayName: "Crypto Kaleo", uiHandle: "@crypto_kaleo" },
  base_beacon: { displayName: "Cobie", uiHandle: "@cobie" },
  cobie_demo: { displayName: "Cobie", uiHandle: "@cobie" },
  meme_marshal: { displayName: "Murad", uiHandle: "@murad" },
  murad_demo: { displayName: "Murad", uiHandle: "@murad" },
  defi_dahlia: { displayName: "Michael van de Poppe", uiHandle: "@michael_vandepoppe" },
  michael_vandepoppe_demo: { displayName: "Michael van de Poppe", uiHandle: "@michael_vandepoppe" },
  ai_arden: { displayName: "Alex Becker", uiHandle: "@alex_becker" },
  alex_becker_demo: { displayName: "Alex Becker", uiHandle: "@alex_becker" },
  wallet_wren: { displayName: "Loomdart", uiHandle: "@loomdart" },
  loomdart_demo: { displayName: "Loomdart", uiHandle: "@loomdart" },
  liquidity_luca: { displayName: "Daan Crypto Trades", uiHandle: "@daan_crypto" },
  daan_crypto_demo: { displayName: "Daan Crypto Trades", uiHandle: "@daan_crypto" },
  builder_brynn: { displayName: "Mert", uiHandle: "@mert" },
  mert_demo: { displayName: "Mert", uiHandle: "@mert" },
  risk_rhea: { displayName: "ZachXBT", uiHandle: "@zachxbt" },
  zachxbt_demo: { displayName: "ZachXBT", uiHandle: "@zachxbt" },
  narrative_niko: { displayName: "Pentoshi", uiHandle: "@pentoshi" },
  pentoshi_demo: { displayName: "Pentoshi", uiHandle: "@pentoshi" },
  flow_faiza: { displayName: "Arthur Hayes", uiHandle: "@arthur_hayes" },
  arthur_hayes_demo: { displayName: "Arthur Hayes", uiHandle: "@arthur_hayes" },
  token_tori: { displayName: "Altcoin Sherpa", uiHandle: "@altcoin_sherpa" },
  altcoin_sherpa_demo: { displayName: "Altcoin Sherpa", uiHandle: "@altcoin_sherpa" },
  chain_chase: { displayName: "Miles Deutscher", uiHandle: "@miles_deutscher" },
  miles_deutscher_demo: { displayName: "Miles Deutscher", uiHandle: "@miles_deutscher" },
  yield_yara: { displayName: "Crypto Cred", uiHandle: "@crypto_cred" },
  crypto_cred_demo: { displayName: "Crypto Cred", uiHandle: "@crypto_cred" },
  alpha_avery: { displayName: "EmperorBTC", uiHandle: "@emperorbtc" },
  emperorbtc_demo: { displayName: "EmperorBTC", uiHandle: "@emperorbtc" },
  chart_cedric: { displayName: "CrediBULL Crypto", uiHandle: "@credibull" },
  credibull_demo: { displayName: "CrediBULL Crypto", uiHandle: "@credibull" },
  dune_dara: { displayName: "Ki Young Ju", uiHandle: "@ki_young_ju" },
  ki_young_ju_demo: { displayName: "Ki Young Ju", uiHandle: "@ki_young_ju" },
};

function resolveDemoKolIdentity(handle: string, displayName: string | null | undefined) {
  const alias = DEMO_KOL_ALIASES[handle];
  return {
    name: alias?.displayName ?? safeName(displayName, titleCase(handle)),
    uiHandle: alias?.uiHandle ?? `@${handle}`,
  };
}

export function tokenKey(chainId: string, contractAddress: string) {
  return `${chainId}:${contractAddress}`;
}

export function buildInitials(value: string) {
  const parts = value
    .split(/\s+/)
    .map((part) => part.trim())
    .filter(Boolean);

  if (parts.length === 0) {
    return "TT";
  }

  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }

  return `${parts[0][0] ?? ""}${parts[1][0] ?? ""}`.toUpperCase();
}

function formatCompactCurrency(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "N/A";
  }

  if (Math.abs(value) >= 1_000_000_000) {
    return `$${(value / 1_000_000_000).toFixed(2)}B`;
  }

  if (Math.abs(value) >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(2)}M`;
  }

  if (Math.abs(value) >= 1_000) {
    return `$${(value / 1_000).toFixed(1)}K`;
  }

  if (Math.abs(value) >= 1) {
    return `$${value.toFixed(2)}`;
  }

  return `$${value.toPrecision(3)}`;
}

function toTier(score: number): ReliabilityTier {
  if (score >= 72) {
    return "good";
  }

  if (score >= 46) {
    return "mixed";
  }

  return "bad";
}

function toSignalType(sentiment: string | null | undefined): SignalType {
  if (sentiment === "bearish") {
    return "bearish";
  }

  if (sentiment === "bullish") {
    return "bullish";
  }

  return "neutral";
}

function toRiskLevel(value: string | null | undefined): AuditRiskLevel | null {
  const normalized = value?.trim().toLowerCase();
  if (normalized === "low" || normalized === "medium" || normalized === "high") {
    return normalized;
  }
  return null;
}

function buildKolScore(
  priority: number | null | undefined,
  postCount: number,
  resolvedMentionCount: number,
) {
  const safePriority = priority ?? 20;
  const priorityScore = 96 - (safePriority - 1) * 2.6;
  const activityBonus = Math.min(10, postCount * 2);
  const mentionBonus = Math.min(8, resolvedMentionCount * 3);

  return Math.round(clamp(priorityScore + activityBonus + mentionBonus, 24, 96));
}

function buildFollowersLabel(item: KOLListItemResponse) {
  if (item.resolved_mention_count > 0) {
    return `${item.resolved_mention_count} resolved mention${item.resolved_mention_count === 1 ? "" : "s"}`;
  }

  return `${item.post_count} tracked post${item.post_count === 1 ? "" : "s"}`;
}

function buildTrackRecordLabel(ranking: KOLRankingItemResponse | undefined, fallback: string) {
  if (!ranking) {
    return fallback;
  }

  if (ranking.evaluated_calls > 0) {
    return `${ranking.evaluated_calls} evaluated call${ranking.evaluated_calls === 1 ? "" : "s"}`;
  }

  return `${ranking.total_calls} tracked call${ranking.total_calls === 1 ? "" : "s"}`;
}

function derivePrimaryAsset(category: string | null | undefined, fallback = "Market watch") {
  if (!category) {
    return fallback;
  }

  return titleCase(category);
}

function buildValidationChecks(checks: ValidationResponse["checks"]): ValidationCheckView[] {
  return checks.map((check) => ({
    name: check.name,
    status: check.status,
    expected: check.expected,
    actual: check.actual,
    fixHint: check.fix_hint,
  }));
}

function buildChainInfo(chains: ChainOptionResponse[]): ChainInfo[] {
  return chains.map((chain) => ({
    chainId: chain.chain_id,
    name: chain.name,
    shortName: chain.short_name,
    enabled: chain.enabled,
  }));
}

function isPlaceholderMarketContainer(
  item: TokenListItemResponse,
  trending: TrendingTokenResponse | undefined,
  insight: InsightItemResponse | undefined,
) {
  const hasIdentity = Boolean(item.symbol?.trim() || item.name?.trim());
  const hasMarketContext = [
    item.latest_price,
    item.latest_percent_change_24h,
    item.latest_volume_24h,
    item.latest_market_cap,
    item.holders,
    trending?.price,
    trending?.percent_change_24h,
    trending?.volume_24h,
    trending?.liquidity,
    trending?.holders,
  ].some((value) => value !== null && value !== undefined);

  return !hasIdentity && !hasMarketContext;
}

function buildAssetFromTokenListItem(
  item: TokenListItemResponse,
  trending: TrendingTokenResponse | undefined,
  insight: InsightItemResponse | undefined,
): AssetData {
  const fallbackSymbol = item.symbol?.trim() || item.contract_address.slice(0, 6).toUpperCase();
  const fallbackName = item.name?.trim() || `${item.chain_short_name} token`;
  const key = tokenKey(item.chain_id, item.contract_address);

  return {
    key,
    symbol: fallbackSymbol,
    name: fallbackName,
    chainId: item.chain_id,
    chainName: item.chain_name,
    chainShortName: item.chain_short_name,
    contractAddress: item.contract_address,
    iconUrl: item.icon_url,
    price: trending?.price ?? item.latest_price,
    change24h: trending?.percent_change_24h ?? item.latest_percent_change_24h,
    volume24h: formatCompactCurrency(trending?.volume_24h ?? item.latest_volume_24h),
    volume24hValue: trending?.volume_24h ?? item.latest_volume_24h,
    marketCap: formatCompactCurrency(item.latest_market_cap),
    marketCapValue: item.latest_market_cap,
    holders: item.holders,
    liquidity: trending?.liquidity ?? null,
    attentionScore: trending?.attention_score ?? insight?.attention_score ?? null,
    label: trending?.label ?? insight?.label ?? null,
    riskLevel: toRiskLevel(item.risk_level_enum),
    description:
      insight?.summary ??
      `${safeName(item.name, fallbackSymbol)} is tracked on ${item.chain_name} with ${
        item.risk_level_enum ? `${item.risk_level_enum.toLowerCase()} audit risk` : "limited audit coverage"
      }.`,
    summary: insight?.summary ?? null,
    updatedAt: trending?.updated_at ?? item.updated_at,
  };
}

function buildKolFromListItem(
  item: KOLListItemResponse,
  dataMode: "seed" | "live",
  ranking?: KOLRankingItemResponse,
): KOL {
  const identity = resolveDemoKolIdentity(item.handle, item.display_name);
  const name = identity.name;
  const fallbackScore = buildKolScore(item.priority, item.post_count, item.resolved_mention_count);
  const score = Math.round(ranking?.track_record_score ?? fallbackScore);

  return {
    id: item.handle,
    name,
    handle: identity.uiHandle,
    initials: buildInitials(name),
    reliabilityScore: score,
    tier: toTier(score),
    followers: buildTrackRecordLabel(ranking, buildFollowersLabel(item)),
    verified: false,
    callCount: ranking?.total_calls ?? item.post_count,
    evaluatedCalls: ranking?.evaluated_calls ?? 0,
    hits: ranking?.hits ?? 0,
    misses: ranking?.misses ?? 0,
    hitRate: ranking?.hit_rate ?? null,
    averageReturn24h: ranking?.average_return_24h ?? null,
    sampleSizeConfidence: ranking?.sample_size_confidence ?? null,
    scoreLabel: ranking?.label ?? "Insufficient Sample",
    explanation: ranking?.explanation ?? null,
    updatedAt: ranking?.updated_at ?? null,
    primaryAsset: derivePrimaryAsset(item.category),
    walletCount: 0,
    dataMode,
    resolvedMentionCount: item.resolved_mention_count,
    category: item.category,
  };
}

function findAssetFromFeedMentions(
  feedItem: KOLFeedItemResponse,
  assets: Record<string, AssetData>,
): AssetData | undefined {
  const resolvedMention = feedItem.mentions.find(
    (mention) => mention.chain_id && mention.contract_address,
  );

  if (resolvedMention?.chain_id && resolvedMention.contract_address) {
    return assets[tokenKey(resolvedMention.chain_id, resolvedMention.contract_address)];
  }

  const symbolMention = feedItem.mentions.find((mention) => mention.symbol_text);
  if (!symbolMention?.symbol_text) {
    return undefined;
  }

  const normalized = symbolMention.symbol_text.trim().toUpperCase();
  const matches = Object.values(assets).filter((asset) => asset.symbol.toUpperCase() === normalized);
  if (matches.length === 1) {
    return matches[0];
  }

  return undefined;
}

function buildFeedCall(feedItem: KOLFeedItemResponse, assets: Record<string, AssetData>): Call {
  const matchedAsset = findAssetFromFeedMentions(feedItem, assets);
  const firstMention = feedItem.mentions[0];
  const engagement =
    (feedItem.like_count ?? 0) +
    (feedItem.repost_count ?? 0) +
    (feedItem.reply_count ?? 0);

  return {
    id: String(feedItem.post_id),
    kolId: feedItem.kol.handle,
    asset:
      matchedAsset?.name ??
      safeName(firstMention?.symbol_text, feedItem.kol.display_name ?? feedItem.kol.handle),
    symbol: matchedAsset?.symbol ?? safeName(firstMention?.symbol_text, "WATCH"),
    type: toSignalType(feedItem.sentiment),
    timestamp: feedItem.created_at,
    snippet: feedItem.text,
    currentPrice: matchedAsset?.price ?? undefined,
    sourceUrl: feedItem.url,
    chainId: matchedAsset?.chainId ?? firstMention?.chain_id ?? null,
    chainName: matchedAsset?.chainName ?? firstMention?.chain_name ?? null,
    contractAddress: matchedAsset?.contractAddress ?? firstMention?.contract_address ?? null,
    engagement,
  };
}

function cleanAlertTitle(value: string | null | undefined) {
  if (!value) {
    return "Audit alert";
  }

  return value
    .replace(/\s+Not Found$/i, "")
    .replace(/\s+Not Detected$/i, "")
    .replace(/\s+Found$/i, "")
    .trim();
}

function alertSeverity(title: string) {
  const normalized = title.trim().toLowerCase();

  if (
    normalized.includes("rug pull") ||
    normalized.includes("honeypot") ||
    normalized.includes("fake token") ||
    normalized.includes("scam risk")
  ) {
    return 5;
  }

  if (
    normalized.includes("trading may be paused") ||
    normalized.includes("paused") ||
    normalized.includes("freezable") ||
    normalized.includes("closable") ||
    normalized.includes("balance manipulation") ||
    normalized.includes("malicious creator")
  ) {
    return 4;
  }

  if (
    normalized.includes("mintable") ||
    normalized.includes("upgradeable") ||
    normalized.includes("modifiable tax") ||
    normalized.includes("unusual sell tax") ||
    normalized.includes("unusual buy tax") ||
    normalized.includes("liquidity risk")
  ) {
    return 3;
  }

  if (
    normalized.includes("metadata mutable") ||
    normalized.includes("wash trading") ||
    normalized.includes("token risk warning")
  ) {
    return 1;
  }

  return 2;
}

function riskPriority(value: AuditRiskLevel | null | undefined) {
  if (value === "high") {
    return 3;
  }
  if (value === "medium") {
    return 2;
  }
  if (value === "low") {
    return 1;
  }
  return 0;
}

function buildActiveAlerts(
  details: TokenDetailResponse[],
  assets: Record<string, AssetData>,
): ActiveAlert[] {
  const alerts = details.flatMap((detail) => {
    const riskLevel = toRiskLevel(detail.audit?.risk_level_enum);
    const triggeredTitles =
      detail.audit?.risk_items.flatMap((item) =>
        item.details
          .filter((riskDetail) => riskDetail.isHit)
          .map((riskDetail) => cleanAlertTitle(riskDetail.title)),
      ) ?? [];

    const uniqueTitles = [...new Set(triggeredTitles)].filter(Boolean);
    const emergencyTitles = uniqueTitles
      .filter((title) => alertSeverity(title) >= 5)
      .sort((left, right) => alertSeverity(right) - alertSeverity(left));
    const severeHighRiskTitles =
      riskLevel === "high"
        ? uniqueTitles
            .filter((title) => alertSeverity(title) >= 4)
            .sort((left, right) => alertSeverity(right) - alertSeverity(left))
        : [];
    const prioritizedTitles =
      emergencyTitles.length > 0 ? emergencyTitles : severeHighRiskTitles;

    if (prioritizedTitles.length === 0) {
      return [];
    }

    const key = tokenKey(detail.token.chain_id, detail.token.contract_address);
    const asset = assets[key];
    const symbol = safeName(
      detail.token.symbol,
      detail.token.contract_address.slice(0, 6).toUpperCase(),
    );
    const tokenName = safeName(detail.token.name, symbol);
    const titles =
      prioritizedTitles.length > 0
        ? prioritizedTitles.slice(0, 3)
        : ["High audit risk classification"];

    return [
      {
        id: `${key}:${titles.join("|")}`,
        chainId: detail.token.chain_id,
        chainName: detail.token.chain_name,
        contractAddress: detail.token.contract_address,
        symbol,
        tokenName,
        riskLevel,
        attentionScore: detail.insight?.attention_score ?? asset?.attentionScore ?? null,
        label: detail.insight?.label ?? asset?.label ?? null,
        titles,
        triggeredCount: prioritizedTitles.length || 1,
        updatedAt:
          detail.audit?.ts ??
          detail.source_freshness.audit_at ??
          detail.insight?.generated_at ??
          detail.token.updated_at,
      },
    ];
  });

  return alerts.sort((left, right) => {
    const riskDiff = riskPriority(right.riskLevel) - riskPriority(left.riskLevel);
    if (riskDiff !== 0) {
      return riskDiff;
    }

    if (right.triggeredCount !== left.triggeredCount) {
      return right.triggeredCount - left.triggeredCount;
    }

    const titleSeverityDiff = alertSeverity(right.titles[0] ?? "") - alertSeverity(left.titles[0] ?? "");
    if (titleSeverityDiff !== 0) {
      return titleSeverityDiff;
    }

    return (right.attentionScore ?? -1) - (left.attentionScore ?? -1);
  });
}

export function adaptAppSnapshot(input: {
  agentHealth: AgentHealthResponse;
  validation: ValidationResponse;
  tokenList: TokenListResponse;
  trending: { items: TrendingTokenResponse[]; available_chains: ChainOptionResponse[] };
  insights: { items: InsightItemResponse[] };
  kols: KOLListResponse;
  kolRankings: KOLRankingsResponse;
  feed: { items: KOLFeedItemResponse[] };
  alertDetails: TokenDetailResponse[];
}): AppSnapshot {
  const trendingByKey = new Map(
    input.trending.items.map((item) => [tokenKey(item.chain_id, item.contract_address), item]),
  );
  const insightByKey = new Map(
    input.insights.items.map((item) => [tokenKey(item.chain_id, item.contract_address), item]),
  );

  const assets = Object.fromEntries(
    input.tokenList.items
      .filter((item) => {
        const key = tokenKey(item.chain_id, item.contract_address);
        return !isPlaceholderMarketContainer(
          item,
          trendingByKey.get(key),
          insightByKey.get(key),
        );
      })
      .map((item) => {
        const key = tokenKey(item.chain_id, item.contract_address);
        return [
          key,
          buildAssetFromTokenListItem(item, trendingByKey.get(key), insightByKey.get(key)),
        ];
      }),
  );

  const assetList = Object.values(assets).sort((left, right) => {
    const leftAttention = left.attentionScore ?? -1;
    const rightAttention = right.attentionScore ?? -1;
    if (leftAttention !== rightAttention) {
      return rightAttention - leftAttention;
    }

    const leftCap = left.marketCapValue ?? -1;
    const rightCap = right.marketCapValue ?? -1;
    return rightCap - leftCap;
  });

  const rankingsByHandle = new Map(
    input.kolRankings.items.map((item) => [item.handle, item]),
  );

  const kols = Object.fromEntries(
    input.kols.items.map((item) => [
      item.handle,
      buildKolFromListItem(item, input.kols.data_mode, rankingsByHandle.get(item.handle)),
    ]),
  );

  const feed = input.feed.items.map((item) => buildFeedCall(item, assets));

  for (const call of feed) {
    const kol = kols[call.kolId];
    if (!kol) {
      continue;
    }

    if (!kol.latestActivityAt || new Date(call.timestamp) > new Date(kol.latestActivityAt)) {
      kol.latestActivityAt = call.timestamp;
    }

    if (!kol.primaryAsset || kol.primaryAsset === "Market watch") {
      kol.primaryAsset = call.symbol;
    }
  }

  const kolList = Object.values(kols).sort(
    (left, right) => right.reliabilityScore - left.reliabilityScore,
  );
  const activeAlerts = buildActiveAlerts(input.alertDetails, assets);

  return {
    agentMode: input.agentHealth.agent_mode,
    dataMode: input.agentHealth.data_mode,
    openaiReady: input.agentHealth.openai_ready,
    validationStatus: input.validation.status,
    validationChecks: buildValidationChecks(input.validation.checks),
    availableChains: buildChainInfo(input.trending.available_chains),
    assets,
    assetList,
    activeAlerts,
    kols,
    kolList,
    feed,
  };
}

function formatTrackedSince(value: string | null) {
  if (!value) {
    return null;
  }

  const createdAt = new Date(value);
  if (Number.isNaN(createdAt.getTime())) {
    return null;
  }

  const ageMs = Date.now() - createdAt.getTime();
  const ageDays = Math.max(1, Math.floor(ageMs / (1000 * 60 * 60 * 24)));
  if (ageDays < 30) {
    return `${ageDays}d`;
  }

  const ageMonths = Math.max(1, Math.floor(ageDays / 30));
  if (ageMonths < 12) {
    return `${ageMonths}mo`;
  }

  return `${(ageDays / 365).toFixed(1)}y`;
}

function mapMention(mention: {
  post_id?: number | null;
  post_created_at?: string | null;
  chain_id?: string | null;
  chain_name?: string | null;
  contract_address?: string | null;
  symbol_text?: string | null;
  mention_type: string;
  is_resolved: boolean;
  confidence?: number | null;
  token_symbol?: string | null;
  token_name?: string | null;
  sentiment?: string | null;
  text?: string | null;
  url?: string | null;
}): KOLMentionView {
  return {
    postId: mention.post_id,
    postCreatedAt: mention.post_created_at,
    chainId: mention.chain_id ?? null,
    chainName: mention.chain_name ?? null,
    contractAddress: mention.contract_address ?? null,
    symbolText: mention.symbol_text ?? null,
    mentionType: mention.mention_type,
    isResolved: mention.is_resolved,
    confidence: mention.confidence ?? null,
    tokenSymbol: mention.token_symbol ?? null,
    tokenName: mention.token_name ?? null,
    sentiment: mention.sentiment ?? null,
    text: mention.text ?? null,
    url: mention.url ?? null,
  };
}

function getOutcomeLabel(call: KOLTrackRecordCallResponse): Call["outcome"] {
  if (call.evaluation_status === "evaluated") {
    return call.is_hit ? "win" : "loss";
  }

  if (call.evaluation_status === "skipped_neutral") {
    return "skipped";
  }

  return "pending";
}

function getWindowPrice(call: KOLTrackRecordCallResponse) {
  switch (call.primary_window) {
    case "1h":
      return call.price_1h;
    case "6h":
      return call.price_6h;
    case "24h":
      return call.price_24h;
    case "7d":
      return call.price_7d;
    default:
      return call.price_24h ?? call.price_6h ?? call.price_1h ?? call.price_7d ?? null;
  }
}

function mapTrackRecordCall(
  call: KOLTrackRecordCallResponse,
  postsById: Map<number, KOLDetailResponse["recent_posts"][number]>,
): Call {
  const matchedPost = postsById.get(call.post_id);
  const symbol = call.token_symbol ?? call.symbol_text ?? "WATCH";

  return {
    id: String(call.call_id),
    kolId: "",
    asset: call.token_name ?? symbol,
    symbol,
    type: toSignalType(call.direction),
    timestamp: call.post_created_at,
    snippet: matchedPost?.text ?? `${symbol} mention tracked for historical alignment.`,
    priceAtCall: call.price_at_post ?? undefined,
    currentPrice: getWindowPrice(call) ?? undefined,
    outcome: getOutcomeLabel(call),
    priceWindow: call.primary_window,
    returnPct: call.primary_return !== null && call.primary_return !== undefined
      ? call.primary_return * 100
      : null,
    status: call.evaluation_status,
    chainId: call.chain_id,
    chainName: call.chain_name,
    contractAddress: call.contract_address,
    sourceUrl: matchedPost?.url ?? null,
  };
}

export function adaptKolDetail(
  detail: KOLDetailResponse,
  trackRecord?: KOLTrackRecordResponse,
): KOLDetailView {
  const resolvedMentionCount = detail.mentions.filter((mention) => mention.is_resolved).length;
  const fallbackScore = buildKolScore(
    detail.profile.priority,
    detail.recent_posts.length,
    resolvedMentionCount,
  );
  const score = Math.round(trackRecord?.score.track_record_score ?? fallbackScore);
  const identity = resolveDemoKolIdentity(detail.profile.handle, detail.profile.display_name);
  const name = identity.name;
  const primaryMention = detail.mentions.find((mention) => mention.symbol_text)?.symbol_text;
  const postsById = new Map(detail.recent_posts.map((post) => [post.id, post]));

  const kol: KOL = {
    id: detail.profile.handle,
    name,
    handle: identity.uiHandle,
    initials: buildInitials(name),
    reliabilityScore: score,
    tier: toTier(score),
    followers:
      trackRecord && trackRecord.score.evaluated_calls > 0
        ? `${trackRecord.score.evaluated_calls} evaluated call${
            trackRecord.score.evaluated_calls === 1 ? "" : "s"
          }`
        : `${detail.recent_posts.length} recent post${detail.recent_posts.length === 1 ? "" : "s"}`,
    verified: false,
    callCount: trackRecord?.score.total_calls ?? detail.recent_posts.length,
    evaluatedCalls: trackRecord?.score.evaluated_calls ?? 0,
    hits: trackRecord?.score.hits ?? 0,
    misses: trackRecord?.score.misses ?? 0,
    hitRate: trackRecord?.score.hit_rate ?? null,
    averageReturn24h: trackRecord?.score.average_return_24h ?? null,
    sampleSizeConfidence: trackRecord?.score.sample_size_confidence ?? null,
    scoreLabel: trackRecord?.score.label ?? "Insufficient Sample",
    explanation:
      trackRecord?.score.evaluated_calls && trackRecord.score.evaluated_calls > 0
        ? `${trackRecord.score.hits} aligned and ${trackRecord.score.misses} misaligned evaluated calls in the tracked dataset.`
        : "Not enough evaluated directional calls yet to draw a strong historical alignment view.",
    updatedAt: trackRecord?.score.updated_at ?? null,
    primaryAsset: primaryMention ?? derivePrimaryAsset(detail.profile.category),
    walletAddress: undefined,
    walletAddresses: [],
    walletCount: 0,
    notes: detail.profile.notes,
    dataMode: detail.profile.data_mode,
    latestActivityAt: detail.recent_posts[0]?.created_at ?? null,
    resolvedMentionCount,
    category: detail.profile.category,
  };

  const recentPosts: KOLPostView[] = detail.recent_posts.map((post) => ({
    id: String(post.id),
    createdAt: post.created_at,
    text: post.text,
    url: post.url,
    likeCount: post.like_count ?? 0,
    repostCount: post.repost_count ?? 0,
    replyCount: post.reply_count ?? 0,
    viewCount: post.view_count ?? 0,
    sentiment:
      post.sentiment === "bullish" || post.sentiment === "bearish" || post.sentiment === "neutral"
        ? post.sentiment
        : "unknown",
    resolvedMentionCount: post.resolved_mention_count,
  }));

  return {
    kol,
    notes: detail.profile.notes,
    trackedSince: formatTrackedSince(detail.profile.created_at),
    wallets: [],
    recentPosts,
    mentions: detail.mentions.map(mapMention),
    trackRecord: {
      score,
      label: trackRecord?.score.label ?? "Insufficient Sample",
      methodology:
        trackRecord?.methodology ??
        "KOL rankings are based on post-event token movement after tracked KOL mentions. They are correlation-based, sample-size adjusted, and not financial advice.",
      disclaimer:
        trackRecord?.disclaimer ??
        "This is correlation-based market research only and not financial advice.",
      totalCalls: trackRecord?.score.total_calls ?? detail.recent_posts.length,
      evaluatedCalls: trackRecord?.score.evaluated_calls ?? 0,
      hits: trackRecord?.score.hits ?? 0,
      misses: trackRecord?.score.misses ?? 0,
      hitRate: trackRecord?.score.hit_rate ?? null,
      averageReturn24h: trackRecord?.score.average_return_24h ?? null,
      sampleSizeConfidence: trackRecord?.score.sample_size_confidence ?? 0,
      updatedAt: trackRecord?.score.updated_at ?? null,
    },
    callHistory: trackRecord?.recent_calls.map((call) => mapTrackRecordCall(call, postsById)) ?? [],
    evaluatedCallHistory:
      trackRecord?.evaluated_calls.items.map((call) => mapTrackRecordCall(call, postsById)) ?? [],
    pendingCallHistory:
      trackRecord?.pending_calls.items.map((call) => mapTrackRecordCall(call, postsById)) ?? [],
  };
}

function riskLevelToAuditStatus(isHit: boolean, riskType: string | null): AuditCheck["status"] {
  if (!isHit) {
    return "pass";
  }

  if (riskType?.toUpperCase() === "CAUTION") {
    return "warning";
  }

  return "fail";
}

function buildAuditRecommendation(risk: AuditRiskLevel, hasAudit: boolean) {
  if (!hasAudit) {
    return "Audit coverage is limited for this token in the current dataset. Use the market, social, and smart-money context together before drawing conclusions.";
  }

  if (risk === "high") {
    return "Multiple risk flags are present in the latest stored audit. Treat this token cautiously and review contract behavior independently.";
  }

  if (risk === "medium") {
    return "Some caution flags are present in the latest stored audit. Use this as a research input rather than a decision shortcut.";
  }

  return "The latest stored audit shows relatively lighter risk, but contract reviews should still be combined with live market and social context.";
}

export function adaptTokenAudit(detail: TokenDetailResponse): TokenAuditResult | null {
  const audit = detail.audit;
  const overallRisk = toRiskLevel(audit?.risk_level_enum) ?? (audit?.has_result ? "medium" : null);
  if (!overallRisk) {
    return null;
  }

  const checks: AuditCheck[] =
    audit?.risk_items.flatMap((item) =>
      item.details.map((riskDetail) => ({
        id: `${item.id}:${riskDetail.title}`,
        label: riskDetail.title,
        status: riskLevelToAuditStatus(riskDetail.isHit, riskDetail.riskType),
        detail: riskDetail.description ?? item.description ?? "No detail available.",
      })),
    ) ?? [
      {
        id: "audit:unavailable",
        label: "Audit coverage",
        status: "warning",
        detail: "No stored audit details are available for this tracked token yet.",
      },
    ];

  return {
    contract: detail.token.contract_address,
    chainId: detail.token.chain_id,
    chainName: detail.token.chain_name,
    symbol: safeName(detail.token.symbol, detail.token.contract_address.slice(0, 6).toUpperCase()),
    name: safeName(detail.token.name, `${detail.token.chain_short_name} token`),
    overallRisk,
    checks: checks.slice(0, 10),
    recommendation: buildAuditRecommendation(overallRisk, Boolean(audit?.has_result)),
    summary: detail.insight?.summary ?? null,
    lastUpdatedAt: audit?.ts ?? detail.source_freshness.audit_at,
  };
}

function buildAssetFromTokenDetail(detail: TokenDetailResponse): AssetData {
  const latestMarket = detail.latest_market;
  return {
    key: tokenKey(detail.token.chain_id, detail.token.contract_address),
    symbol: safeName(detail.token.symbol, detail.token.contract_address.slice(0, 6).toUpperCase()),
    name: safeName(detail.token.name, `${detail.token.chain_short_name} token`),
    chainId: detail.token.chain_id,
    chainName: detail.token.chain_name,
    chainShortName: detail.token.chain_short_name,
    contractAddress: detail.token.contract_address,
    iconUrl: detail.token.icon_url,
    price: latestMarket?.price ?? null,
    change24h: latestMarket?.percent_change_24h ?? null,
    volume24h: formatCompactCurrency(latestMarket?.volume_24h),
    volume24hValue: latestMarket?.volume_24h ?? null,
    marketCap: formatCompactCurrency(latestMarket?.market_cap),
    marketCapValue: latestMarket?.market_cap ?? null,
    holders: latestMarket?.holders ?? null,
    liquidity: latestMarket?.liquidity ?? null,
    attentionScore: detail.insight?.attention_score ?? null,
    label: detail.insight?.label ?? null,
    riskLevel: toRiskLevel(detail.audit?.risk_level_enum),
    description: detail.insight?.summary ?? undefined,
    summary: detail.insight?.summary ?? null,
    updatedAt: detail.token.updated_at,
  };
}

function buildFallbackSummary(detail: TokenDetailResponse) {
  const assetName = safeName(detail.token.symbol, detail.token.contract_address.slice(0, 6).toUpperCase());
  const market = detail.latest_market;

  if (!market) {
    return `${assetName} is tracked locally, but recent market context is limited right now.`;
  }

  return `${assetName} is being tracked on ${detail.token.chain_name} with ${formatCompactCurrency(
    market.volume_24h,
  )} in 24h volume and ${formatCompactCurrency(market.liquidity)} of liquidity.`;
}

export function adaptMarketDetail(detail: TokenDetailResponse): MarketDetailView {
  const asset = buildAssetFromTokenDetail(detail);
  const audit = adaptTokenAudit(detail);
  const latestMarket = detail.latest_market;

  const smartMoneySignals: SmartMoneySignalView[] = detail.smart_money_signals.map((signal) => ({
    signalId: signal.signal_id,
    direction: signal.direction ?? "unknown",
    smartMoneyCount: signal.smart_money_count,
    signalTriggerTime: signal.signal_trigger_time,
    totalTokenValue: signal.total_token_value,
    alertPrice: signal.alert_price,
    currentPrice: signal.current_price,
    highestPrice: signal.highest_price,
    exitRate: signal.exit_rate,
    status: signal.status,
    maxGain: signal.max_gain,
  }));

  return {
    asset,
    summary: detail.insight?.summary ?? buildFallbackSummary(detail),
    attentionScore: detail.insight?.attention_score ?? null,
    label: detail.insight?.label ?? null,
    scoreBreakdown: {
      market: detail.insight?.market_score ?? null,
      kol: detail.insight?.kol_score ?? null,
      smartMoney: detail.insight?.smart_money_score ?? null,
      safety: detail.insight?.safety_score ?? null,
    },
    latestMarket: {
      ts: latestMarket?.ts ?? null,
      price: latestMarket?.price ?? null,
      percentChange1h: latestMarket?.percent_change_1h ?? null,
      percentChange4h: latestMarket?.percent_change_4h ?? null,
      percentChange24h: latestMarket?.percent_change_24h ?? null,
      volume24h: latestMarket?.volume_24h ?? null,
      liquidity: latestMarket?.liquidity ?? null,
      marketCap: latestMarket?.market_cap ?? null,
      fdv: latestMarket?.fdv ?? null,
      holders: latestMarket?.holders ?? null,
      top10HoldersPct: latestMarket?.top10_holders_pct ?? null,
      kolHolders: latestMarket?.kol_holders ?? null,
      kolHoldingPct: latestMarket?.kol_holding_pct ?? null,
      smartMoneyHoldingPct: latestMarket?.smart_money_holding_pct ?? null,
    },
    audit,
    rawRiskItems:
      detail.audit?.risk_items.map((item) => ({
        id: item.id,
        name: item.name,
        description: item.description,
        details: item.details.map((riskDetail) => ({
          title: riskDetail.title,
          description: riskDetail.description,
          isHit: riskDetail.isHit,
          riskType: riskDetail.riskType,
        })),
      })) ?? [],
    smartMoneySignals,
    kolMentions: detail.kol_mentions.map(mapMention),
    freshness: {
      marketSnapshotAt: detail.source_freshness.market_snapshot_at,
      auditAt: detail.source_freshness.audit_at,
      latestSmartMoneyAt: detail.source_freshness.latest_smart_money_at,
      latestKolPostAt: detail.source_freshness.latest_kol_post_at,
      insightAt: detail.source_freshness.insight_at,
      kolDataMode: detail.source_freshness.kol_data_mode,
    },
    links: detail.token.links ?? [],
  };
}
