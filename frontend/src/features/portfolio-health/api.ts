import { api } from "@/lib/api/client";
import type { HealthScoreResponse, RiskAlertsResponse } from "@/lib/api/types";

export async function fetchHealthScore(): Promise<HealthScoreResponse> {
  return api.get<HealthScoreResponse>("/api/v1/portfolio/health-score");
}

export async function fetchRiskAlerts(): Promise<RiskAlertsResponse> {
  return api.get<RiskAlertsResponse>("/api/v1/portfolio/alerts");
}
