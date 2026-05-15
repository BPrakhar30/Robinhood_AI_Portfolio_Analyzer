"use client";

/**
 * DataPrefetcher — fires React Query prefetch calls the moment the
 * authenticated app shell mounts, before the user has navigated anywhere.
 *
 * This mirrors the pattern ChatHydrator uses for chat sessions: render
 * nothing, side-effect only. Markets news and portfolio news are the two
 * endpoints with the heaviest perceived latency (LLM enrichment) so they
 * benefit most from being warm in the cache by the time the user opens
 * the Markets page.
 */

import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { fetchMarketNews } from "@/features/markets/api";
import { fetchPortfolioNews } from "@/features/stocks/api";
import { fetchMacroAlerts, fetchMacroPulse } from "@/features/macro/api";

export function DataPrefetcher() {
  const queryClient = useQueryClient();

  useEffect(() => {
    // Fire-and-forget — React Query deduplicates concurrent calls so even
    // if a page component mounts simultaneously the network request is only
    // issued once.
    queryClient.prefetchQuery({
      queryKey: ["markets", "news"],
      queryFn: fetchMarketNews,
      staleTime: 5 * 60_000,
    });

    queryClient.prefetchQuery({
      queryKey: ["markets", "portfolio-news"],
      queryFn: fetchPortfolioNews,
      staleTime: 30_000,
    });

    queryClient.prefetchQuery({
      queryKey: ["macro", "alerts"],
      queryFn: fetchMacroAlerts,
      staleTime: 5 * 60_000,
    });

    // Macro Pulse is the heaviest call (LLM enrichment) — start it immediately
    // so the page is warm in cache before the user navigates there.
    queryClient.prefetchQuery({
      queryKey: ["macro", "pulse"],
      queryFn: fetchMacroPulse,
      staleTime: 15 * 60_000,
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return null;
}
