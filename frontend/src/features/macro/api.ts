import { api } from "@/lib/api/client";
import type { MacroAlertsResponse, MacroPulseResponse } from "./types";

export async function fetchMacroPulse(): Promise<MacroPulseResponse> {
  return api.get<MacroPulseResponse>("/api/v1/macro/pulse");
}

export async function fetchMacroAlerts(): Promise<MacroAlertsResponse> {
  return api.get<MacroAlertsResponse>("/api/v1/macro/alerts");
}
