/**
 * Shared TypeScript types for API responses. They mirror backend Pydantic schemas;
 * keep them aligned manually when the API changes (no codegen yet).
 *
 * Added: 2026-04-03
 */
export interface UserResponse {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_email_verified: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface RegistrationResponse {
  message: string;
  email: string;
  requires_verification: boolean;
}

export interface MessageResponse {
  message: string;
}

export interface BrokerConnectionResponse {
  id: number;
  broker_type: string;
  status: string;
  last_sync_at: string | null;
  created_at: string;
}

export interface PositionResponse {
  symbol: string;
  name: string;
  quantity: number;
  average_cost: number;
  current_price: number;
  purchase_date: string | null;
  realized_gains: number;
  unrealized_gains: number;
  asset_type: string;
  sector: string | null;
  currency: string;
  total_amount_invested: number;
  market_value: number;
  weight_percent: number;
}

export interface TransactionResponse {
  symbol: string;
  transaction_type: string;
  quantity: number;
  price: number;
  total_amount: number;
  fees: number;
  executed_at: string;
}

export interface AccountSummaryResponse {
  total_value: number;
  cash_balance: number;
  positions_count: number;
  buying_power: number;
  total_realized_gains: number;
  total_unrealized_gains: number;
}

export interface SyncStatusResponse {
  broker_type: string;
  status: string;
  last_sync_at: string | null;
  positions_count: number;
  error_message: string | null;
}

export interface CSVTemplateResponse {
  template: string;
  columns: string[];
  required_columns: string[];
}

export interface HealthResponse {
  status: string;
  service: string;
  environment: string;
  timestamp: string;
}

export interface StatusResponse {
  status: string;
  components: {
    api: string;
    database: string;
  };
  version: string;
  timestamp: string;
}

export interface RobinhoodInitiateResponse {
  status: "authenticated" | "mfa_required";
  mfa_type?: "sms" | "email" | "app" | "prompt";
  data?: Record<string, unknown> | null;
}

export interface APIStandardResponse {
  status: string;
  data: Record<string, unknown> | null;
  error_message: string | null;
  timestamp: string;
}
