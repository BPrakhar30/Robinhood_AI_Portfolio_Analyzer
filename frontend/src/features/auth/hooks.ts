"use client";
/**
 * React Query hooks for auth: current user, login, register, verify, resend, logout.
 *
 * - `useRegister` navigates to `/verify-email` on success.
 * - `useLogin` invalidates `["auth"]` queries and redirects to `/dashboard`.
 * - `useResendVerification` is shared by the login and registration flows.
 *
 * Added: 2026-04-03
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useAuthStore } from "./store";
import {
  loginUser,
  registerUser,
  fetchCurrentUser,
  verifyEmail,
  resendVerification,
  deleteAccount,
} from "./api";
import type { LoginFormData, RegisterFormData } from "./schemas";

export function useCurrentUser() {
  const { setUser, setLoading } = useAuthStore();

  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: async () => {
      try {
        const user = await fetchCurrentUser();
        setUser(user);
        return user;
      } catch {
        // Unauthenticated or network failure: stop blocking the shell without throwing.
        setLoading(false);
        return null;
      }
    },
    retry: false,
    staleTime: 5 * 60 * 1000,
  });
}

export function useLogin() {
  const { setUser } = useAuthStore();
  const router = useRouter();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: LoginFormData) => {
      await loginUser(data);
      const user = await fetchCurrentUser();
      return user;
    },
    onSuccess: (user) => {
      setUser(user);
      queryClient.invalidateQueries({ queryKey: ["auth"] });
      router.push("/dashboard");
    },
  });
}

export function useRegister() {
  const router = useRouter();

  return useMutation({
    mutationFn: async (data: RegisterFormData) => {
      const { confirmPassword, ...registerData } = data;
      return registerUser(registerData);
    },
    onSuccess: (response) => {
      router.push(`/verify-email?email=${encodeURIComponent(response.email)}`);
    },
  });
}

export function useVerifyEmail() {
  const router = useRouter();

  return useMutation({
    mutationFn: async (data: { email: string; code: string }) =>
      verifyEmail(data),
    onSuccess: () => {
      router.push("/login?verified=true");
    },
  });
}

export function useResendVerification() {
  return useMutation({
    mutationFn: async (email: string) => resendVerification(email),
  });
}

export function useLogout() {
  const { logout } = useAuthStore();
  const router = useRouter();
  const queryClient = useQueryClient();

  return () => {
    logout();
    queryClient.clear();
    router.push("/login");
  };
}

export function useDeleteAccount() {
  const { logout } = useAuthStore();
  const router = useRouter();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteAccount,
    onSuccess: () => {
      logout();
      queryClient.clear();
      router.push("/login");
    },
  });
}
