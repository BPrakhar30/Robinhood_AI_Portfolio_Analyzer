"use client";
/**
 * Registration page with password strength UI. On 409 (account exists), offers
 * resend verification or login. Submit/actions use native `<button>` elements
 * (not shadcn `Button`) so React Hook Form submission and `type="button"`
 * actions behave reliably.
 *
 * Added: 2026-04-03
 */
import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { TrendingUp, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { registerSchema, type RegisterFormData } from "@/features/auth/schemas";
import { useRegister, useResendVerification } from "@/features/auth/hooks";
import { useRouter } from "next/navigation";
import { APIError } from "@/lib/api/client";

export default function RegisterPage() {
  const registerMutation = useRegister();
  const resendMutation = useResendVerification();
  const router = useRouter();
  const [existingEmail, setExistingEmail] = useState<string | null>(null);
  const [existingVerified, setExistingVerified] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  const password = watch("password", "");
  const passwordStrength = getPasswordStrength(password);

  const onSubmit = (data: RegisterFormData) => {
    setExistingEmail(null);
    setExistingVerified(false);
    registerMutation.mutate(data, {
      onError: (error) => {
        if (error instanceof APIError && error.status === 409) {
          setExistingEmail(data.email);
          setExistingVerified(error.detail?.is_verified === true);
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
          <h1 className="text-2xl font-semibold tracking-tight">Create your account</h1>
          <p className="text-sm text-muted-foreground">
            Start analyzing your portfolio with AI
          </p>
        </div>

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
                <Label htmlFor="full_name">Full name</Label>
                <Input
                  id="full_name"
                  placeholder="Jane Smith"
                  autoComplete="name"
                  {...register("full_name")}
                />
                {errors.full_name && (
                  <p className="text-xs text-destructive">{errors.full_name.message}</p>
                )}
              </div>

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
                  autoComplete="new-password"
                  {...register("password")}
                />
                {password && (
                  <div className="space-y-1">
                    <div className="flex gap-1">
                      {[1, 2, 3, 4].map((i) => (
                        <div
                          key={i}
                          className={`h-1 flex-1 rounded-full ${
                            i <= passwordStrength.score
                              ? passwordStrength.color
                              : "bg-muted"
                          }`}
                        />
                      ))}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {passwordStrength.label}
                    </p>
                  </div>
                )}
                {errors.password && (
                  <p className="text-xs text-destructive">{errors.password.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Confirm password</Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  placeholder="••••••••"
                  autoComplete="new-password"
                  {...register("confirmPassword")}
                />
                {errors.confirmPassword && (
                  <p className="text-xs text-destructive">{errors.confirmPassword.message}</p>
                )}
              </div>

              {registerMutation.isError && existingEmail && existingVerified && (
                <Alert className="border-amber-500/30 bg-amber-500/5">
                  <AlertDescription className="text-amber-700 dark:text-amber-400 text-sm space-y-2 text-center">
                    <p>An account with this email already exists.</p>
                    <Link
                      href="/login"
                      className="underline font-medium text-amber-800 dark:text-amber-300 text-sm cursor-pointer"
                    >
                      Log in to your account
                    </Link>
                  </AlertDescription>
                </Alert>
              )}

              {registerMutation.isError && existingEmail && !existingVerified && (
                <Alert className="border-amber-500/30 bg-amber-500/5">
                  <AlertDescription className="text-amber-700 dark:text-amber-400 text-sm space-y-2">
                    <p>An account with this email exists but is not yet verified.</p>
                    <div className="flex flex-row items-center gap-3">
                      <button
                        type="button"
                        className="underline font-medium text-amber-800 dark:text-amber-300 text-sm cursor-pointer"
                        disabled={resendMutation.isPending}
                        onClick={() => {
                          resendMutation.mutate(existingEmail, {
                            onSuccess: () => {
                              router.push(
                                `/verify-email?email=${encodeURIComponent(existingEmail)}`
                              );
                            },
                          });
                        }}
                      >
                        {resendMutation.isPending
                          ? "Sending..."
                          : "Resend verification code"}
                      </button>
                      <span className="text-amber-400">|</span>
                      <Link
                        href="/login"
                        className="underline font-medium text-amber-800 dark:text-amber-300 text-sm cursor-pointer"
                      >
                        Log in
                      </Link>
                    </div>
                  </AlertDescription>
                </Alert>
              )}

              {registerMutation.isError && !existingEmail && (
                <Alert variant="destructive">
                  <AlertDescription className="text-sm">
                    {(registerMutation.error as Error)?.message ||
                      "Registration failed. Please try again."}
                  </AlertDescription>
                </Alert>
              )}

              <button
                type="submit"
                className={cn(buttonVariants(), "w-full")}
                disabled={registerMutation.isPending}
              >
                {registerMutation.isPending && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                Create account
              </button>
            </form>
          </CardContent>
        </Card>

        <p className="text-center text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link
            href="/login"
            className="font-medium text-foreground hover:underline"
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}

function getPasswordStrength(password: string) {
  let score = 0;
  if (password.length >= 8) score++;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
  if (/\d/.test(password)) score++;
  if (/[^a-zA-Z0-9]/.test(password)) score++;

  const labels = ["", "Weak", "Fair", "Good", "Strong"];
  const colors = [
    "",
    "bg-red-500",
    "bg-amber-500",
    "bg-emerald-400",
    "bg-emerald-600",
  ];

  return { score, label: labels[score] || "", color: colors[score] || "" };
}
