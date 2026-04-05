"use client";
/**
 * Login page: email/password form, success banners from query params, and handling
 * for unverified accounts. On 403-style “verify your email” errors, the submitted
 * email is stored so the user can resend a code and go to `/verify-email`.
 *
 * Added: 2026-04-03
 */
import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { TrendingUp, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { loginSchema, type LoginFormData } from "@/features/auth/schemas";
import { useLogin, useResendVerification } from "@/features/auth/hooks";

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}

function LoginForm() {
  const searchParams = useSearchParams();
  const registered = searchParams.get("registered") === "true";
  const verified = searchParams.get("verified") === "true";
  const router = useRouter();
  const login = useLogin();
  const resendMutation = useResendVerification();
  const [unverifiedEmail, setUnverifiedEmail] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
    getValues,
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = (data: LoginFormData) => {
    setUnverifiedEmail(null);
    login.mutate(data, {
      onError: (error: Error) => {
        // Backend signals unverified user; show resend CTA instead of generic error.
        if (error.message?.toLowerCase().includes("verify your email")) {
          setUnverifiedEmail(data.email);
        }
      },
    });
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-muted/30">
      <div className="w-full max-w-md space-y-6">
        <div className="flex flex-col items-center space-y-2">
          <Link href="/" className="flex items-center gap-2 mb-4">
            <div className="h-10 w-10 rounded-xl bg-primary flex items-center justify-center">
              <TrendingUp className="h-5 w-5 text-primary-foreground" />
            </div>
          </Link>
          <h1 className="text-2xl font-semibold tracking-tight">Welcome back</h1>
          <p className="text-sm text-muted-foreground">
            Sign in to your portfolio copilot
          </p>
        </div>

        {registered && (
          <Alert className="border-emerald-500/30 bg-emerald-500/5">
            <AlertDescription className="text-emerald-700 dark:text-emerald-400 text-sm">
              Account created successfully! You can now sign in.
            </AlertDescription>
          </Alert>
        )}

        {verified && (
          <Alert className="border-emerald-500/30 bg-emerald-500/5">
            <AlertDescription className="text-emerald-700 dark:text-emerald-400 text-sm">
              Email verified! You can now sign in.
            </AlertDescription>
          </Alert>
        )}

        <Card>
          <CardContent className="pt-6">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSubmit(onSubmit)();
              }}
              className="space-y-4"
            >
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  autoComplete="email"
                  {...register("email")}
                />
                {errors.email && (
                  <p className="text-xs text-destructive">{errors.email.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  autoComplete="current-password"
                  {...register("password")}
                />
                {errors.password && (
                  <p className="text-xs text-destructive">{errors.password.message}</p>
                )}
              </div>

              {login.isError && !unverifiedEmail && (
                <Alert variant="destructive">
                  <AlertDescription className="text-sm">
                    {(login.error as Error)?.message ||
                      "Invalid credentials. Please try again."}
                  </AlertDescription>
                </Alert>
              )}

              {unverifiedEmail && (
                <Alert className="border-amber-500/30 bg-amber-500/5">
                  <AlertDescription className="text-amber-700 dark:text-amber-400 text-sm space-y-2">
                    <p>Please verify your email address before logging in.</p>
                    <button
                      type="button"
                      className="underline font-medium text-amber-800 dark:text-amber-300"
                      disabled={resendMutation.isPending}
                      onClick={() => {
                        resendMutation.mutate(unverifiedEmail, {
                          onSuccess: () => {
                            router.push(
                              `/verify-email?email=${encodeURIComponent(unverifiedEmail)}`
                            );
                          },
                        });
                      }}
                    >
                      {resendMutation.isPending
                        ? "Sending..."
                        : "Resend code & verify"}
                    </button>
                  </AlertDescription>
                </Alert>
              )}

              <button
                type="submit"
                className={cn(buttonVariants(), "w-full")}
                disabled={login.isPending}
              >
                {login.isPending && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                Sign in
              </button>
            </form>
          </CardContent>
        </Card>

        <p className="text-center text-sm text-muted-foreground">
          Don&apos;t have an account?{" "}
          <Link
            href="/register"
            className="font-medium text-foreground hover:underline"
          >
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
