"use client";
/**
 * React Query hooks for auth: current user, login, register, verify, resend, logout.
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useAuthStore } from "./store";
import { useChatStore } from "@/features/chat/store";
import {
  loginUser,
  registerUser,
  fetchCurrentUser,
  verifyEmail,
  resendVerification,
  forgotPassword,
  resetPassword,
  logoutUser,
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
        // Unauthenticated / network failure: unblock the shell.
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

  return async () => {
    try {
      await logoutUser();
    } catch {
      // Best-effort server-side revocation; clear local state regardless.
    }
    logout();
    useChatStore.getState().reset();
    queryClient.clear();
    router.push("/login");
  };
}

export function useForgotPassword() {
  return useMutation({
    mutationFn: async (email: string) => forgotPassword(email),
  });
}

export function useResetPassword() {
  const router = useRouter();

  return useMutation({
    mutationFn: async (data: { token: string; new_password: string }) =>
      resetPassword(data),
    onSuccess: () => {
      router.push("/login?reset=true");
    },
  });
}

export function useDeleteAccount() {
  const { logout } = useAuthStore();
  const router = useRouter();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteAccount,
    onSuccess: () => {
      logout();
      useChatStore.getState().reset();
      queryClient.clear();
      router.push("/login");
    },
  });
}
