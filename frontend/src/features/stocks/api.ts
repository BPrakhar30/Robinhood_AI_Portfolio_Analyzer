import { api } from "@/lib/api/client";
import type {
  CandleRange,
  PortfolioNewsResponse,
  StockCandles,
  StockDetailResponse,
  StockUniverseResponse,
} from "./types";

export async function fetchStockUniverse(params: {
  universe?: "all" | "owned";
  search?: string;
  liveQuotes?: boolean;
  limit?: number;
} = {}): Promise<StockUniverseResponse> {
  const q = new URLSearchParams();
  q.set("universe", params.universe ?? "all");
  if (params.search) q.set("search", params.search);
  if (params.liveQuotes === false) q.set("live_quotes", "false");
  if (params.limit) q.set("limit", String(params.limit));
  return api.get<StockUniverseResponse>(`/api/v1/stocks?${q.toString()}`);
}

export async function fetchStockDetail(symbol: string): Promise<StockDetailResponse> {
  return api.get<StockDetailResponse>(
    `/api/v1/stocks/${encodeURIComponent(symbol)}`,
  );
}

export async function fetchStockCandles(
  symbol: string,
  range: CandleRange,
): Promise<StockCandles> {
  return api.get<StockCandles>(
    `/api/v1/stocks/${encodeURIComponent(symbol)}/candles?range=${range}`,
  );
}

export async function fetchPortfolioNews(): Promise<PortfolioNewsResponse> {
  return api.get<PortfolioNewsResponse>("/api/v1/markets/portfolio-news");
}
