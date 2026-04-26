export type CandleRange = "1D" | "1W" | "1M" | "3M" | "YTD" | "1Y" | "5Y" | "MAX";
export type StockAssetType =
  | "stock"
  | "etf"
  | "crypto"
  | "option"
  | "mutual_fund"
  | "bond"
  | "cash"
  | "unknown";

export interface StockProfile {
  symbol: string;
  name: string;
  asset_type: StockAssetType;
  exchange?: string | null;
  currency: string;
  country?: string | null;
  sector?: string | null;
  industry?: string | null;
  website?: string | null;
  logo?: string | null;
  description?: string | null;
  ceo?: string | null;
  employees?: number | null;
  headquarters?: string | null;
  founded?: number | null;
  ipo_date?: string | null;
}

export interface StockQuote {
  symbol: string;
  price?: number | null;
  previous_close?: number | null;
  open?: number | null;
  day_high?: number | null;
  day_low?: number | null;
  volume?: number | null;
  change?: number | null;
  change_percent?: number | null;
  currency: string;
  market_state?: string | null;
  as_of?: string | null;
}

export interface CandlePoint {
  t: string;
  o: number;
  h: number;
  l: number;
  c: number;
  v?: number | null;
}

export interface StockCandles {
  symbol: string;
  range: CandleRange;
  interval: string;
  points: CandlePoint[];
  start_price?: number | null;
  end_price?: number | null;
  change?: number | null;
  change_percent?: number | null;
}

export interface StockKeyStats {
  symbol: string;
  market_cap?: number | null;
  pe_ratio?: number | null;
  forward_pe?: number | null;
  dividend_yield?: number | null;
  eps_ttm?: number | null;
  beta?: number | null;
  average_volume?: number | null;
  volume?: number | null;
  day_high?: number | null;
  day_low?: number | null;
  open_price?: number | null;
  fifty_two_week_high?: number | null;
  fifty_two_week_low?: number | null;
  short_ratio?: number | null;
  shares_outstanding?: number | null;
}

export interface EarningsQuarter {
  date: string;
  quarter?: number | null;
  year?: number | null;
  eps_estimate?: number | null;
  eps_actual?: number | null;
  revenue_estimate?: number | null;
  revenue_actual?: number | null;
  hour?: string | null;
  surprise?: "beat" | "miss" | "inline" | null;
  surprise_percent?: number | null;
  reported: boolean;
}

export interface StockEarnings {
  symbol: string;
  next_event?: EarningsQuarter | null;
  history: EarningsQuarter[];
}

export interface StockNewsItem {
  id?: string | null;
  symbol?: string | null;
  headline: string;
  summary: string;
  ai_summary?: string | null;
  source: string;
  source_url?: string | null;
  url: string;
  image?: string | null;
  published_at: string;
  time_ago: string;
}

export interface StockPositionSummary {
  symbol: string;
  owned: boolean;
  shares: number;
  average_cost?: number | null;
  market_value?: number | null;
  total_invested?: number | null;
  todays_return?: number | null;
  todays_return_percent?: number | null;
  total_return?: number | null;
  total_return_percent?: number | null;
  portfolio_weight_percent?: number | null;
  asset_type?: string | null;
}

export interface StockDetailResponse {
  symbol: string;
  profile: StockProfile;
  quote: StockQuote;
  key_stats: StockKeyStats;
  earnings: StockEarnings;
  position: StockPositionSummary;
  news: StockNewsItem[];
}

export interface StockCard {
  symbol: string;
  name: string;
  sector?: string | null;
  asset_type: StockAssetType;
  owned: boolean;
  price?: number | null;
  change_percent?: number | null;
}

export interface StockUniverseResponse {
  items: StockCard[];
  total: number;
  owned_count: number;
}

export interface PortfolioNewsResponse {
  articles: StockNewsItem[];
  symbols: string[];
  updated_at: string;
}
