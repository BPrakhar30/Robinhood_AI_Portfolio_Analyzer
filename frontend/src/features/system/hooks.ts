"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import type { HealthResponse, StatusResponse } from "@/lib/api/types";

export function useHealth() {
  return useQuery({
    queryKey: ["system", "health"],
    queryFn: () => api.get<HealthResponse>("/health"),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

export function useStatus() {
  return useQuery({
    queryKey: ["system", "status"],
    queryFn: () => api.get<StatusResponse>("/status"),
    staleTime: 30_000,
  });
}
