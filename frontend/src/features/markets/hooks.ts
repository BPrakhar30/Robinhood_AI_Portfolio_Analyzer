import { useQuery } from "@tanstack/react-query";
import {
  fetchMarketNews,
  fetchEarningsCalendar,
  fetchEarningsForDate,
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
