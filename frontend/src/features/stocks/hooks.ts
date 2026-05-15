import { useQuery } from "@tanstack/react-query";
import type { CandleRange } from "./types";
import {
  fetchPortfolioNews,
  fetchStockAnalysis,
  fetchStockCandles,
  fetchStockDetail,
  fetchStockUniverse,
} from "./api";

export function useStockUniverse(params: {
  universe?: "all" | "owned";
  search?: string;
  liveQuotes?: boolean;
} = {}) {
  const key = [
    "stocks",
    "universe",
    params.universe ?? "all",
    params.search ?? "",
    params.liveQuotes ?? true,
  ] as const;
  return useQuery({
    queryKey: key,
    queryFn: () => fetchStockUniverse(params),
    staleTime: 60_000,
  });
}

export function useStockDetail(symbol: string | undefined) {
  return useQuery({
    queryKey: ["stocks", "detail", symbol],
    queryFn: () => fetchStockDetail(symbol!),
    enabled: !!symbol,
    staleTime: 60_000,
  });
}

export function useStockCandles(
  symbol: string | undefined,
  range: CandleRange,
) {
  return useQuery({
    queryKey: ["stocks", "candles", symbol, range],
    queryFn: () => fetchStockCandles(symbol!, range),
    enabled: !!symbol,
    staleTime: range === "1D" || range === "1W" ? 60_000 : 15 * 60_000,
  });
}

export function useStockAnalysis(symbol: string | undefined) {
  return useQuery({
    queryKey: ["stocks", "analysis", symbol],
    queryFn: () => fetchStockAnalysis(symbol!),
    enabled: !!symbol,
    staleTime: 15 * 60_000,
    retry: 1,
  });
}

export function usePortfolioNews(options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: ["markets", "portfolio-news"],
    queryFn: fetchPortfolioNews,
    enabled: options.enabled ?? true,
    staleTime: 5 * 60_000,
    refetchInterval: 5 * 60_000,
    retry: 3,
    retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 10_000),
  });
}
