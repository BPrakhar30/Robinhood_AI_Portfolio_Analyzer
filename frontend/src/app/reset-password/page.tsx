"use client";

import { Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { TrendingUp, Loader2, ShieldCheck } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  resetPasswordSchema,
  type ResetPasswordFormData,
} from "@/features/auth/schemas";
import { useResetPassword } from "@/features/auth/hooks";

export default function ResetPasswordPage() {
  return (
    <Suspense>
      <ResetPasswordForm />
    </Suspense>
  );
}

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const mutation = useResetPassword();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetPasswordFormData>({
    resolver: zodResolver(resetPasswordSchema),
  });

  const onSubmit = (data: ResetPasswordFormData) => {
    if (!token) return;
    mutation.mutate({ token, new_password: data.password });
  };

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4 bg-muted/30">
        <div className="w-full max-w-md space-y-6">
          <div className="flex flex-col items-center space-y-2">
            <Link href="/" className="flex items-center gap-2 mb-4">
              <div className="h-10 w-10 rounded-xl bg-primary flex items-center justify-center">
                <TrendingUp className="h-5 w-5 text-primary-foreground" />
              </div>
            </Link>
            <h1 className="text-2xl font-semibold tracking-tight">
              Invalid reset link
            </h1>
          </div>
          <Card>
            <CardContent className="py-8 text-center">
              <p className="text-sm text-muted-foreground mb-4">
                This password reset link is invalid or has expired.
              </p>
              <Link
                href="/forgot-password"
                className={cn(buttonVariants(), "w-full")}
              >
                Request a new link
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-muted/30">
      <div className="w-full max-w-md space-y-6">
        <div className="flex flex-col items-center space-y-2">
          <Link href="/" className="flex items-center gap-2 mb-4">
            <div className="h-10 w-10 rounded-xl bg-primary flex items-center justify-center">
              <TrendingUp className="h-5 w-5 text-primary-foreground" />
            </div>
          </Link>
          <div className="mx-auto w-fit rounded-full bg-primary/10 p-3">
            <ShieldCheck className="h-6 w-6 text-primary" />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Set a new password
          </h1>
          <p className="text-sm text-muted-foreground">
            Choose a strong password for your account.
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
                <Label htmlFor="password">New password</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  autoComplete="new-password"
                  autoFocus
                  {...register("password")}
                />
                {errors.password && (
                  <p className="text-xs text-destructive">
                    {errors.password.message}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Confirm new password</Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  placeholder="••••••••"
                  autoComplete="new-password"
                  {...register("confirmPassword")}
                />
                {errors.confirmPassword && (
                  <p className="text-xs text-destructive">
                    {errors.confirmPassword.message}
                  </p>
                )}
              </div>

              {mutation.isError && (
                <Alert variant="destructive">
                  <AlertDescription className="text-sm">
                    {(mutation.error as Error)?.message ||
                      "Something went wrong. Please try again."}
                  </AlertDescription>
                </Alert>
              )}

              <button
                type="submit"
                className={cn(buttonVariants(), "w-full")}
                disabled={mutation.isPending}
              >
                {mutation.isPending && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                Reset password
              </button>
            </form>
          </CardContent>
        </Card>

        <p className="text-center text-sm text-muted-foreground">
          <Link
            href="/login"
            className="font-medium text-foreground hover:underline cursor-pointer"
          >
            Back to sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
