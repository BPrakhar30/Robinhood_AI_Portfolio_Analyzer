import { api } from "@/lib/api/client";
import type {
  EarningsCalendarResponse,
  EarningsEntry,
  EarningsHighlightsResponse,
  EarningsListResponse,
  MarketNewsResponse,
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

/**
 * Request the AI-generated highlights brief for a single earnings event.
 * We forward the known figures so the LLM can reason over them without
 * having to re-fetch the estimate/actual pair itself.
 */
export async function fetchEarningsHighlights(
  entry: Pick<
    EarningsEntry,
    | "symbol"
    | "company"
    | "quarter"
    | "year"
    | "eps_estimate"
    | "eps_actual"
    | "revenue_estimate"
    | "revenue_actual"
  > & { reported?: boolean }
): Promise<EarningsHighlightsResponse> {
  const params = new URLSearchParams({
    symbol: entry.symbol,
    quarter: String(entry.quarter),
    year: String(entry.year),
    company: entry.company ?? "",
    reported: String(entry.reported ?? entry.eps_actual != null),
  });
  if (entry.eps_estimate != null)
    params.set("eps_estimate", String(entry.eps_estimate));
  if (entry.eps_actual != null)
    params.set("eps_actual", String(entry.eps_actual));
  if (entry.revenue_estimate != null)
    params.set("revenue_estimate", String(entry.revenue_estimate));
  if (entry.revenue_actual != null)
    params.set("revenue_actual", String(entry.revenue_actual));

  return api.get<EarningsHighlightsResponse>(
    `/api/v1/markets/earnings/highlights?${params.toString()}`
  );
}
