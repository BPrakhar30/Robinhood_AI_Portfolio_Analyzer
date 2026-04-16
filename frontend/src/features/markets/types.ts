export interface MarketHeadline {
  title: string;
  summary: string;
  source: string;
  url: string;
}

export interface RecentDevelopment {
  source: string;
  time_ago: string;
  title: string;
  excerpt: string;
  url: string;
}

export interface MarketNewsResponse {
  summary: {
    headlines: MarketHeadline[];
    updated_at: string;
  };
  developments: {
    articles: RecentDevelopment[];
    updated_at: string;
  };
  sources: string[];
}

export interface EarningsDay {
  date: string;
  day_label: string;
  earnings_count: number;
  symbols: string[];
}

export interface EarningsCalendarResponse {
  week: EarningsDay[];
  selected_date: string;
}

export interface EarningsEntry {
  symbol: string;
  company: string;
  date: string;
  hour: string;
  quarter: number;
  year: number;
  eps_estimate: number | null;
  eps_actual: number | null;
  revenue_estimate: number | null;
  revenue_actual: number | null;
}

export interface EarningsListResponse {
  entries: EarningsEntry[];
  date: string;
}
