import { api } from "@/lib/api/client";
import type { MarketNewsResponse } from "./types";

export async function fetchMarketNews(): Promise<MarketNewsResponse> {
  return api.get<MarketNewsResponse>("/api/v1/markets/news");
}
