import { useQuery } from "@tanstack/react-query";
import { fetchHealthScore, fetchRiskAlerts } from "./api";

export function useHealthScore() {
  return useQuery({
    queryKey: ["portfolio", "health-score"],
    queryFn: fetchHealthScore,
    staleTime: 60_000,
  });
}

export function useRiskAlerts() {
  return useQuery({
    queryKey: ["portfolio", "alerts"],
    queryFn: fetchRiskAlerts,
    staleTime: 60_000,
  });
}
