"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { TrendingUp, Loader2, ArrowLeft, Mail } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  forgotPasswordSchema,
  type ForgotPasswordFormData,
} from "@/features/auth/schemas";
import { useForgotPassword } from "@/features/auth/hooks";

export default function ForgotPasswordPage() {
  const mutation = useForgotPassword();
  const [submitted, setSubmitted] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    getValues,
  } = useForm<ForgotPasswordFormData>({
    resolver: zodResolver(forgotPasswordSchema),
  });

  const onSubmit = (data: ForgotPasswordFormData) => {
    mutation.mutate(data.email, {
      onSuccess: () => setSubmitted(true),
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
          <h1 className="text-2xl font-semibold tracking-tight">
            Reset your password
          </h1>
          <p className="text-sm text-muted-foreground text-center">
            Enter your email and we&apos;ll send you a link to reset your password.
          </p>
        </div>

        <Card>
          <CardContent className="pt-6">
            {submitted ? (
              <div className="text-center space-y-4 py-4">
                <div className="mx-auto w-fit rounded-full bg-primary/10 p-3">
                  <Mail className="h-6 w-6 text-primary" />
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-medium">Check your email</p>
                  <p className="text-xs text-muted-foreground">
                    If an account exists for{" "}
                    <span className="font-medium text-foreground">
                      {getValues("email")}
                    </span>
                    , you&apos;ll receive a password reset link shortly.
                  </p>
                </div>
                <button
                  type="button"
                  className={cn(
                    buttonVariants({ variant: "outline" }),
                    "w-full mt-2"
                  )}
                  onClick={() => {
                    setSubmitted(false);
                    mutation.reset();
                  }}
                >
                  Try a different email
                </button>
              </div>
            ) : (
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
                    autoFocus
                    {...register("email")}
                  />
                  {errors.email && (
                    <p className="text-xs text-destructive">
                      {errors.email.message}
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
                  Send reset link
                </button>
              </form>
            )}
          </CardContent>
        </Card>

        <p className="text-center text-sm text-muted-foreground">
          <Link
            href="/login"
            className="font-medium text-foreground hover:underline cursor-pointer inline-flex items-center gap-1"
          >
            <ArrowLeft className="h-3 w-3" />
            Back to sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
