export type Signal = "bullish" | "bearish" | "neutral" | "caution";

export interface MacroIndicator {
  key: string;
  label: string;
  value: number | null;
  display_value: string;
  change: number | null;
  change_display: string;
  signal: Signal;
  signal_label: string;
  description: string;
  portfolio_impact: string;
  detail: string;
  category: "essential" | "important" | "contextual";
  unit: string;
}

export interface PortfolioExposure {
  rate_sensitive_pct: number;
  cyclical_pct: number;
  defensive_pct: number;
  growth_pct: number;
  value_pct: number;
  international_revenue_pct: number;
  energy_pct: number;
  total_positions: number;
  total_market_value: number;
  symbols_by_category: Record<string, string[]>;
}

export interface MacroAlert {
  indicator_key: string;
  indicator_label: string;
  severity: "info" | "warning" | "critical";
  title: string;
  message: string;
  link: string;
}

export interface MacroPulseResponse {
  indicators: MacroIndicator[];
  exposure: PortfolioExposure;
  ai_summary: string | null;
  detailed_summary: string | null;
  alerts: MacroAlert[];
  updated_at: string;
}

export interface MacroAlertsResponse {
  alerts: MacroAlert[];
}
