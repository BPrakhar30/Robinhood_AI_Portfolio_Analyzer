import { useQuery } from "@tanstack/react-query";
import type { EarningsEntry } from "./types";
import {
  fetchEarningsCalendar,
  fetchEarningsForDate,
  fetchEarningsHighlights,
  fetchMarketNews,
} from "./api";

export function useMarketNews() {
  return useQuery({
    queryKey: ["markets", "news"],
    queryFn: fetchMarketNews,
    staleTime: 5 * 60_000,
    refetchInterval: 5 * 60_000,
  });
}

export function useEarningsCalendar(date?: string) {
  return useQuery({
    queryKey: ["markets", "earnings-calendar", date],
    queryFn: () => fetchEarningsCalendar(date),
    staleTime: 15 * 60_000,
  });
}

export function useEarningsForDate(date: string) {
  return useQuery({
    queryKey: ["markets", "earnings-date", date],
    queryFn: () => fetchEarningsForDate(date),
    staleTime: 15 * 60_000,
    enabled: !!date,
  });
}

export function useEarningsHighlights(entry: EarningsEntry | null) {
  return useQuery({
    queryKey: entry
      ? ["markets", "earnings-highlights", entry.symbol, entry.quarter, entry.year]
      : ["markets", "earnings-highlights", "none"],
    queryFn: () =>
      fetchEarningsHighlights({
        symbol: entry!.symbol,
        company: entry!.company,
        quarter: entry!.quarter,
        year: entry!.year,
        eps_estimate: entry!.eps_estimate,
        eps_actual: entry!.eps_actual,
        revenue_estimate: entry!.revenue_estimate,
        revenue_actual: entry!.revenue_actual,
        reported: entry!.eps_actual != null,
      }),
    enabled: !!entry,
    staleTime: 60 * 60_000,
    retry: 1,
  });
}
