export type ReliabilityTier = "good" | "mixed" | "bad";
export type SignalType = "bullish" | "bearish" | "neutral";
export type ValidationState = "pass" | "warn" | "fail";
export type AuditRiskLevel = "low" | "medium" | "high";

export interface KOL {
  id: string;
  name: string;
  handle: string;
  initials: string;
  avatarUrl?: string;
  reliabilityScore: number;
  tier: ReliabilityTier;
  followers: string;
  verified: boolean;
  callCount: number;
  primaryAsset?: string;
  walletAddress?: string;
  walletAddresses?: string[];
  walletCount?: number;
  notes?: string | null;
  dataMode?: "seed" | "live";
  latestActivityAt?: string | null;
  resolvedMentionCount?: number;
  category?: string | null;
}

export interface Call {
  id: string;
  kolId: string;
  asset: string;
  symbol: string;
  type: SignalType;
  timestamp: string;
  snippet: string;
  priceAtCall?: number;
  currentPrice?: number;
  sourceUrl?: string | null;
  chainId?: string | null;
  chainName?: string | null;
  contractAddress?: string | null;
  engagement?: number;
}

export interface AssetData {
  key: string;
  symbol: string;
  name: string;
  chainId: string;
  chainName: string;
  chainShortName: string;
  contractAddress: string;
  iconUrl?: string | null;
  price?: number | null;
  change24h?: number | null;
  volume24h: string;
  volume24hValue?: number | null;
  marketCap: string;
  marketCapValue?: number | null;
  holders?: number | null;
  liquidity?: number | null;
  attentionScore?: number | null;
  label?: string | null;
  riskLevel?: AuditRiskLevel | null;
  description?: string;
  summary?: string | null;
  updatedAt?: string | null;
}

export interface AuditCheck {
  id: string;
  label: string;
  status: "pass" | "warning" | "fail";
  detail: string;
}

export interface TokenAuditResult {
  contract: string;
  chainId: string;
  chainName: string;
  symbol: string;
  name: string;
  overallRisk: AuditRiskLevel;
  checks: AuditCheck[];
  recommendation: string;
  summary?: string | null;
  lastUpdatedAt?: string | null;
}

export interface KOLPostView {
  id: string;
  createdAt: string;
  text: string;
  url?: string | null;
  likeCount: number;
  repostCount: number;
  replyCount: number;
  viewCount: number;
  sentiment: SignalType | "unknown";
  resolvedMentionCount: number;
}

export interface KOLMentionView {
  postId?: number | string | null;
  postCreatedAt?: string | null;
  chainId?: string | null;
  chainName?: string | null;
  contractAddress?: string | null;
  symbolText?: string | null;
  mentionType: string;
  isResolved: boolean;
  confidence?: number | null;
  tokenSymbol?: string | null;
  tokenName?: string | null;
  sentiment?: string | null;
  text?: string | null;
  url?: string | null;
}

export interface SmartMoneySignalView {
  signalId: string;
  direction: string;
  smartMoneyCount: number | null;
  signalTriggerTime: string | null;
  totalTokenValue: number | null;
  alertPrice: number | null;
  currentPrice: number | null;
  highestPrice: number | null;
  exitRate: number | null;
  status: string | null;
  maxGain: number | null;
}

export interface KOLDetailView {
  kol: KOL;
  notes: string | null;
  trackedSince: string | null;
  wallets: Array<{
    chainName: string;
    address: string;
    sourceType: string | null;
    sourceUrl: string | null;
    confidence: number | null;
    createdAt: string | null;
  }>;
  recentPosts: KOLPostView[];
  mentions: KOLMentionView[];
}

export interface MarketDetailView {
  asset: AssetData;
  summary: string;
  attentionScore: number | null;
  label: string | null;
  scoreBreakdown: {
    market: number | null;
    kol: number | null;
    smartMoney: number | null;
    safety: number | null;
  };
  latestMarket: {
    ts: string | null;
    price: number | null;
    percentChange1h: number | null;
    percentChange4h: number | null;
    percentChange24h: number | null;
    volume24h: number | null;
    liquidity: number | null;
    marketCap: number | null;
    fdv: number | null;
    holders: number | null;
    top10HoldersPct: number | null;
    kolHolders: number | null;
    kolHoldingPct: number | null;
    smartMoneyHoldingPct: number | null;
  };
  audit: TokenAuditResult | null;
  rawRiskItems: Array<{
    id: string;
    name: string;
    description: string | null;
    details: Array<{
      title: string;
      description: string | null;
      isHit: boolean;
      riskType: string | null;
    }>;
  }>;
  smartMoneySignals: SmartMoneySignalView[];
  kolMentions: KOLMentionView[];
  freshness: {
    marketSnapshotAt: string | null;
    auditAt: string | null;
    latestSmartMoneyAt: string | null;
    latestKolPostAt: string | null;
    insightAt: string | null;
    kolDataMode: "seed" | "live";
  };
  links: Array<{
    label: string;
    link: string;
  }>;
}

export interface ChainInfo {
  chainId: string;
  name: string;
  shortName: string;
  enabled: boolean;
}

export interface ValidationCheckView {
  name: string;
  status: ValidationState;
  expected: number | string;
  actual: number | string | null;
  fixHint: string;
}

export interface AppSnapshot {
  agentMode: "deterministic" | "openai";
  dataMode: "seed" | "live";
  openaiReady: boolean;
  validationStatus: ValidationState;
  validationChecks: ValidationCheckView[];
  availableChains: ChainInfo[];
  assets: Record<string, AssetData>;
  assetList: AssetData[];
  kols: Record<string, KOL>;
  kolList: KOL[];
  feed: Call[];
}
