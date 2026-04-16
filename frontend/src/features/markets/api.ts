import { api } from "@/lib/api/client";
import type {
  MarketNewsResponse,
  EarningsCalendarResponse,
  EarningsListResponse,
} from "./types";

export async function fetchMarketNews(): Promise<MarketNewsResponse> {
  return api.get<MarketNewsResponse>("/api/v1/markets/news");
}

export async function fetchEarningsCalendar(
  date?: string
): Promise<EarningsCalendarResponse> {
  const params = date ? `?date=${date}` : "";
  return api.get<EarningsCalendarResponse>(
    `/api/v1/markets/earnings/calendar${params}`
  );
}

export async function fetchEarningsForDate(
  date: string
): Promise<EarningsListResponse> {
  return api.get<EarningsListResponse>(
    `/api/v1/markets/earnings/date?date=${date}`
  );
}
