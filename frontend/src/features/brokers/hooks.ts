"use client";
/**
 * React Query layer for brokers: connections, positions, transactions, summary, CSV.
 *
 * Mutations invalidate `["broker"]` so lists and portfolio data refetch together.
 * Stale times: connections/summary 30s, positions/transactions 60s, CSV template
 * `Infinity` (static spec).
 *
 * Added: 2026-04-03
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchConnections,
  connectRobinhood,
  initiateRobinhood,
  completeRobinhoodMFA,
  connectCSV,
  disconnectBroker,
  syncConnection,
  fetchPositions,
  fetchTransactions,
  fetchSummary,
  fetchCSVTemplate,
} from "./api";

export function useConnections() {
  return useQuery({
    queryKey: ["broker", "connections"],
    queryFn: fetchConnections,
    staleTime: 30_000,
  });
}

export function usePositions(connectionId?: number) {
  return useQuery({
    queryKey: ["broker", "positions", connectionId],
    queryFn: () => fetchPositions(connectionId),
    staleTime: 60_000,
  });
}

export function useTransactions(connectionId?: number, limit = 100) {
  return useQuery({
    queryKey: ["broker", "transactions", connectionId, limit],
    queryFn: () => fetchTransactions(connectionId, limit),
    staleTime: 60_000,
  });
}

export function useSummary() {
  return useQuery({
    queryKey: ["broker", "summary"],
    queryFn: fetchSummary,
    staleTime: 30_000,
  });
}

export function useCSVTemplate() {
  return useQuery({
    queryKey: ["broker", "csv-template"],
    queryFn: fetchCSVTemplate,
    staleTime: Infinity,
  });
}

export function useConnectRobinhood() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: connectRobinhood,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["broker"] });
    },
  });
}

export function useInitiateRobinhood() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: initiateRobinhood,
    onSuccess: (data) => {
      if (data.status === "authenticated") {
        qc.invalidateQueries({ queryKey: ["broker"] });
      }
    },
  });
}

export function useCompleteRobinhoodMFA() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: completeRobinhoodMFA,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["broker"] });
    },
  });
}

export function useConnectCSV() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: connectCSV,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["broker"] });
    },
  });
}

export function useDisconnectBroker() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: disconnectBroker,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["broker"] });
    },
  });
}

export function useSyncConnection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: syncConnection,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["broker"] });
    },
  });
}
