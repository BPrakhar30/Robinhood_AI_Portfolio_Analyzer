import { useQuery } from "@tanstack/react-query";
import { fetchMarketNews } from "./api";

export function useMarketNews() {
  return useQuery({
    queryKey: ["markets", "news"],
    queryFn: fetchMarketNews,
    staleTime: 5 * 60_000,
    refetchInterval: 5 * 60_000,
  });
}
