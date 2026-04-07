/**
 * Broker integration API helpers. All routes expect a logged-in user; the shared
 * `api` client attaches the Bearer token automatically.
 *
 * Added: 2026-04-03
 */
import { api } from "@/lib/api/client";
import type {
  BrokerConnectionResponse,
  PositionResponse,
  TransactionResponse,
  AccountSummaryResponse,
  SyncStatusResponse,
  CSVTemplateResponse,
  APIStandardResponse,
  RobinhoodInitiateResponse,
} from "@/lib/api/types";

export async function fetchConnections(): Promise<BrokerConnectionResponse[]> {
  return api.get<BrokerConnectionResponse[]>("/api/v1/broker/connections");
}

export async function connectRobinhood(data: {
  username: string;
  password: string;
  mfa_code?: string;
}): Promise<APIStandardResponse> {
  return api.post<APIStandardResponse>("/api/v1/broker/connect/robinhood", data);
}

export async function initiateRobinhood(data: {
  username: string;
  password: string;
}): Promise<RobinhoodInitiateResponse> {
  return api.post<RobinhoodInitiateResponse>(
    "/api/v1/broker/connect/robinhood/initiate",
    data
  );
}

export async function completeRobinhoodMFA(data: {
  mfa_code: string;
}): Promise<APIStandardResponse> {
  return api.post<APIStandardResponse>(
    "/api/v1/broker/connect/robinhood/complete-mfa",
    data
  );
}

export async function connectPlaidExchange(
  publicToken: string
): Promise<APIStandardResponse> {
  return api.post<APIStandardResponse>("/api/v1/broker/connect/plaid", {
    public_token: publicToken,
  });
}

export async function connectCSV(data: {
  csv_content: string;
  cash_balance: number;
  filename?: string;
}): Promise<APIStandardResponse> {
  return api.post<APIStandardResponse>("/api/v1/broker/connect/csv", data);
}

export async function disconnectBroker(
  connectionId: number
): Promise<APIStandardResponse> {
  return api.post<APIStandardResponse>(
    `/api/v1/broker/connections/${connectionId}/disconnect`
  );
}

export async function deleteConnection(
  connectionId: number
): Promise<APIStandardResponse> {
  return api.delete<APIStandardResponse>(
    `/api/v1/broker/connections/${connectionId}`
  );
}

export async function syncConnection(
  connectionId: number
): Promise<SyncStatusResponse> {
  return api.post<SyncStatusResponse>(
    `/api/v1/broker/connections/${connectionId}/sync`
  );
}

export async function fetchPositions(
  connectionId?: number
): Promise<PositionResponse[]> {
  const params = connectionId ? `?connection_id=${connectionId}` : "";
  return api.get<PositionResponse[]>(`/api/v1/broker/positions${params}`);
}

export async function fetchTransactions(
  connectionId?: number,
  limit: number = 100
): Promise<TransactionResponse[]> {
  const params = new URLSearchParams();
  if (connectionId) params.set("connection_id", String(connectionId));
  if (limit) params.set("limit", String(limit));
  const qs = params.toString() ? `?${params.toString()}` : "";
  return api.get<TransactionResponse[]>(`/api/v1/broker/transactions${qs}`);
}

export async function fetchSummary(): Promise<AccountSummaryResponse> {
  return api.get<AccountSummaryResponse>("/api/v1/broker/summary");
}

export async function fetchCSVTemplate(): Promise<CSVTemplateResponse> {
  return api.get<CSVTemplateResponse>("/api/v1/broker/csv/template");
}
