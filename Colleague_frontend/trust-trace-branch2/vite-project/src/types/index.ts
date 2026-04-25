export type ReliabilityTier = 'good' | 'mixed' | 'bad';

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
  arkhamLink?: string;
  walletHoldings?: {
    symbol: string;
    amount: string;
    value: string;
  }[];
}

export interface Call {
  id: string;
  kolId: string;
  asset: string;
  symbol: string;
  type: 'bullish' | 'bearish';
  timestamp: string;
  outcome?: 'win' | 'loss' | 'pending';
  priceAtCall: number;
  currentPrice?: number;
  snippet: string;
}

export interface AssetData {
  symbol: string;
  name: string;
  price: number;
  change24h: number;
  volume24h: string;
  marketCap: string;
  holders?: number;
  description?: string;
}

export interface AuditCheck {
  id: string;
  label: string;
  status: 'pass' | 'warning' | 'fail';
  detail: string;
}

export interface TokenAuditResult {
  contract: string;
  symbol: string;
  name: string;
  overallRisk: 'low' | 'medium' | 'high';
  checks: AuditCheck[];
  recommendation: string;
}

export type PageType = 'landing' | 'kol-profile' | 'asset-insights' | 'token-audit';

export interface NavigationState {
  page: PageType;
  kolId?: string;
  assetSymbol?: string;
  fromKolId?: string;
}
