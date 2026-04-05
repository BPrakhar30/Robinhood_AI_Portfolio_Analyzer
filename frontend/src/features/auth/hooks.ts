"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { useAuthStore } from "./store";
import {
  loginUser,
  registerUser,
  fetchCurrentUser,
  verifyEmail,
  resendVerification,
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
      toast.success("Welcome back!");
      router.push("/dashboard");
    },
    onError: (error: Error) => {
      toast.error(error.message || "Login failed. Please try again.");
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
      toast.success(response.message);
      router.push(`/verify-email?email=${encodeURIComponent(response.email)}`);
    },
    onError: (error: Error) => {
      toast.error(error.message || "Registration failed. Please try again.");
    },
  });
}

export function useVerifyEmail() {
  const router = useRouter();

  return useMutation({
    mutationFn: async (data: { email: string; code: string }) =>
      verifyEmail(data),
    onSuccess: (response) => {
      toast.success(response.message);
      router.push("/login?verified=true");
    },
    onError: (error: Error) => {
      toast.error(error.message || "Verification failed.");
    },
  });
}

export function useResendVerification() {
  return useMutation({
    mutationFn: async (email: string) => resendVerification(email),
    onSuccess: (response) => {
      toast.success(response.message);
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to resend code.");
    },
  });
}

export function useLogout() {
  const { logout } = useAuthStore();
  const router = useRouter();
  const queryClient = useQueryClient();

  return () => {
    logout();
    queryClient.clear();
    toast.success("Signed out successfully.");
    router.push("/login");
  };
}
