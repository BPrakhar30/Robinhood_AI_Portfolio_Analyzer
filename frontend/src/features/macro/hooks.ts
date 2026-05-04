import { useQuery } from "@tanstack/react-query";
import { fetchMacroAlerts, fetchMacroPulse } from "./api";

export function useMacroPulse(options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: ["macro", "pulse"],
    queryFn: fetchMacroPulse,
    enabled: options.enabled ?? true,
    staleTime: 15 * 60_000,
    refetchInterval: 15 * 60_000,
  });
}

export function useMacroAlerts(options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: ["macro", "alerts"],
    queryFn: fetchMacroAlerts,
    enabled: options.enabled ?? true,
    staleTime: 5 * 60_000,
    refetchInterval: 5 * 60_000,
  });
}
