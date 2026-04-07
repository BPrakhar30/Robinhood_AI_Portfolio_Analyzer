/**
 * Auth API calls (register, verify, login, current user). `loginUser` persists
 * the JWT via `setAuthToken` in sessionStorage immediately after a successful
 * login response.
 *
 * Added: 2026-04-03
 */
import { api, setAuthToken } from "@/lib/api/client";
import type {
  UserResponse,
  TokenResponse,
  RegistrationResponse,
  MessageResponse,
} from "@/lib/api/types";

export async function registerUser(data: {
  email: string;
  password: string;
  full_name?: string;
}): Promise<RegistrationResponse> {
  return api.post<RegistrationResponse>("/api/v1/auth/register", data);
}

export async function verifyEmail(data: {
  email: string;
  code: string;
}): Promise<MessageResponse> {
  return api.post<MessageResponse>("/api/v1/auth/verify-email", data);
}

export async function resendVerification(email: string): Promise<MessageResponse> {
  return api.post<MessageResponse>("/api/v1/auth/resend-verification", { email });
}

export async function loginUser(data: {
  email: string;
  password: string;
}): Promise<TokenResponse> {
  const response = await api.post<TokenResponse>("/api/v1/auth/login", data);
  setAuthToken(response.access_token);
  return response;
}

export async function fetchCurrentUser(): Promise<UserResponse> {
  return api.get<UserResponse>("/api/v1/auth/me");
}

export async function deleteAccount(): Promise<MessageResponse> {
  return api.delete<MessageResponse>("/api/v1/auth/account");
}
