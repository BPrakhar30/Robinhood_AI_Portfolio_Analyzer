/**
 * Centralized HTTP client for the backend API: base URL, JSON, Bearer auth from
 * sessionStorage, and consistent error shaping.
 *
 * Auto-logout (clear token + redirect to /login) runs only on 401 from `/auth/me`
 * and `/auth/login`, not from broker endpoints—so a bad broker session does not
 * sign the user out of the app.
 *
 * Tokens live in sessionStorage (not localStorage) so they disappear when the tab
 * closes.
 *
 * `USER_FRIENDLY_ERRORS` supplies copy when the response has no `detail` /
 * `error_message` field.
 *
 * Added: 2026-04-03
 */
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export interface APIResponse<T = unknown> {
  status: "success" | "error";
  data: T | null;
  error_message: string | null;
  timestamp: string;
}

export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public serverMessage?: string,
    public detail?: Record<string, unknown>
  ) {
    super(message);
    this.name = "APIError";
  }
}

function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem("access_token");
}

export function setAuthToken(token: string): void {
  sessionStorage.setItem("access_token", token);
}

export function clearAuthToken(): void {
  sessionStorage.removeItem("access_token");
}

const USER_FRIENDLY_ERRORS: Record<number, string> = {
  400: "The request was invalid. Please check your input.",
  401: "Your session has expired. Please log in again.",
  403: "You don't have permission to perform this action.",
  404: "The requested resource was not found.",
  409: "This resource already exists.",
  429: "Too many requests. Please wait a moment.",
  500: "Something went wrong on our end. Please try again.",
  502: "The service is temporarily unavailable.",
  504: "The request timed out. Please try again.",
};

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const token = getAuthToken();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let serverMessage = USER_FRIENDLY_ERRORS[response.status] || "An unexpected error occurred.";
      let detailData: Record<string, unknown> | undefined;
      try {
        const errorBody = await response.json();
        if (errorBody.detail) {
          if (typeof errorBody.detail === "object") {
            serverMessage = errorBody.detail.message || serverMessage;
            detailData = errorBody.detail;
          } else {
            serverMessage = errorBody.detail;
          }
        } else if (errorBody.error_message) {
          serverMessage = errorBody.error_message;
        }
      } catch {
        // response body wasn't JSON
      }

      if (response.status === 401) {
        // Narrow scope: broker 401s should surface as errors, not global logout.
        const isAuthEndpoint =
          endpoint.includes("/auth/me") || endpoint.includes("/auth/login");
        if (isAuthEndpoint) {
          clearAuthToken();
          if (typeof window !== "undefined" && !endpoint.includes("/auth/login")) {
            window.location.href = "/login";
          }
        }
      }

      throw new APIError(serverMessage, response.status, serverMessage, detailData);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof APIError) throw error;
    throw new APIError("Network error. Please check your connection.", 0);
  }
}

export const api = {
  get: <T>(endpoint: string) => apiClient<T>(endpoint, { method: "GET" }),

  post: <T>(endpoint: string, body?: unknown) =>
    apiClient<T>(endpoint, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    }),

  put: <T>(endpoint: string, body?: unknown) =>
    apiClient<T>(endpoint, {
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
    }),

  delete: <T>(endpoint: string) => apiClient<T>(endpoint, { method: "DELETE" }),
};
