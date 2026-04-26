export interface MarketSource {
  name: string;
  url: string;
}

export interface MarketHeadline {
  title: string;
  summary: string;
  ai_summary?: string | null;
  source: string;
  url: string;
}

export interface RecentDevelopment {
  source: string;
  time_ago: string;
  title: string;
  excerpt: string;
  ai_summary?: string | null;
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
  sources: MarketSource[];
}
