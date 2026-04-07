"use client";
/**
 * Two-step Robinhood connection form.
 *
 * Step 1: Username + password → calls /initiate
 *         – If MFA required: transition to step 2
 *         – If no MFA: connection is completed immediately
 *
 * Step 2: Depends on the MFA type returned by the backend:
 *   • "sms" / "email" / "app"  → user enters a 6-digit code → calls /complete-mfa
 *   • "prompt" (push notification) → auto-triggers /complete-mfa with a 30-second
 *     countdown while the backend polls Robinhood for approval
 *
 * Updated: 2026-04-07
 */
import { useState, useEffect, useRef, useCallback } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Loader2, Shield, AlertTriangle, ArrowLeft, Smartphone, Bell, CheckCircle2,
} from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { cn } from "@/lib/utils";
import {
  useInitiateRobinhood,
  useCompleteRobinhoodMFA,
} from "@/features/brokers/hooks";

type MFAType = "sms" | "email" | "app" | "prompt";

const PUSH_TIMEOUT_SECONDS = 30;

const credentialsSchema = z.object({
  username: z.string().min(1, "Username is required"),
  password: z.string().min(1, "Password is required"),
});

const mfaSchema = z.object({
  mfa_code: z
    .string()
    .min(6, "Enter the 6-digit code")
    .max(6, "Enter the 6-digit code"),
});

type CredentialsData = z.infer<typeof credentialsSchema>;
type MFAData = z.infer<typeof mfaSchema>;

interface Props {
  onSuccess: () => void;
}

const MFA_MESSAGES: Record<MFAType, string> = {
  sms: "A verification code was sent to your phone via SMS. Enter it below.",
  email: "A verification code was sent to your email. Enter it below.",
  app: "Enter the 6-digit code from your authenticator app (Google Authenticator, Authy, etc.).",
  prompt: "A push notification was sent to your Robinhood app. Approve the login on your phone.",
};

export function RobinhoodConnectForm({ onSuccess }: Props) {
  const [step, setStep] = useState<"credentials" | "mfa" | "authenticated">("credentials");
  const [mfaType, setMfaType] = useState<MFAType | null>(null);
  const [countdown, setCountdown] = useState(PUSH_TIMEOUT_SECONDS);
  const pushTriggered = useRef(false);

  const initiateMutation = useInitiateRobinhood();
  const completeMutation = useCompleteRobinhoodMFA();

  const credentialsForm = useForm<CredentialsData>({
    resolver: zodResolver(credentialsSchema),
  });

  const mfaForm = useForm<MFAData>({
    resolver: zodResolver(mfaSchema),
  });

  const needsCodeInput = mfaType !== "prompt";

  const handlePushSuccess = useCallback(() => {
    setStep("authenticated");
    setTimeout(() => onSuccess(), 1500);
  }, [onSuccess]);

  // Auto-trigger complete-mfa for push notifications
  useEffect(() => {
    if (step !== "mfa" || mfaType !== "prompt" || pushTriggered.current) return;
    pushTriggered.current = true;

    completeMutation.mutateAsync({ mfa_code: "" }).then(() => {
      handlePushSuccess();
    }).catch(() => {
      // error shown inline
    });
  }, [step, mfaType]); // eslint-disable-line react-hooks/exhaustive-deps

  // Countdown timer for push notifications
  useEffect(() => {
    if (step !== "mfa" || mfaType !== "prompt") return;

    setCountdown(PUSH_TIMEOUT_SECONDS);
    const interval = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [step, mfaType]);

  // ── Step 1: send credentials ──
  const onSubmitCredentials = async (data: CredentialsData) => {
    try {
      const result = await initiateMutation.mutateAsync(data);

      if (result.status === "authenticated") {
        onSuccess();
      } else if (result.status === "mfa_required") {
        pushTriggered.current = false;
        setMfaType(result.mfa_type as MFAType);
        setStep("mfa");
      }
    } catch {
      // shown via initiateMutation.isError
    }
  };

  // ── Step 2: send MFA code (SMS/email/app only) ──
  const onSubmitMFA = async (data: MFAData) => {
    try {
      await completeMutation.mutateAsync(data);
      onSuccess();
    } catch {
      // shown via completeMutation.isError
    }
  };

  const handleBack = () => {
    setStep("credentials");
    setMfaType(null);
    pushTriggered.current = false;
    mfaForm.reset();
    initiateMutation.reset();
    completeMutation.reset();
  };

  // ────────── Authenticated via push notification ──────────
  if (step === "authenticated") {
    return (
      <div className="space-y-4">
        <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-4 flex items-center gap-3">
          <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
          <div>
            <p className="text-sm font-medium text-emerald-700 dark:text-emerald-400">
              Authenticated via push notification
            </p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Syncing your portfolio...
            </p>
          </div>
        </div>
        <div className="flex justify-center">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  // ────────── Step 2: MFA screen ──────────
  if (step === "mfa") {
    return (
      <div className="space-y-4">
        {/* Context banner */}
        <div className="rounded-lg bg-muted/50 p-3 flex items-start gap-2">
          {mfaType === "prompt" ? (
            <Bell className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
          ) : (
            <Smartphone className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
          )}
          <p className="text-xs text-muted-foreground">
            {MFA_MESSAGES[mfaType!]}
          </p>
        </div>

        {needsCodeInput ? (
          /* SMS / email / authenticator — code entry */
          <form
            onSubmit={(e) => {
              e.preventDefault();
              mfaForm.handleSubmit(onSubmitMFA)();
            }}
            className="space-y-4"
          >
            <div className="space-y-2">
              <Label htmlFor="rh-mfa-code">Verification Code</Label>
              <Input
                id="rh-mfa-code"
                placeholder="123456"
                maxLength={6}
                inputMode="numeric"
                autoFocus
                {...mfaForm.register("mfa_code")}
              />
              {mfaForm.formState.errors.mfa_code && (
                <p className="text-xs text-destructive">
                  {mfaForm.formState.errors.mfa_code.message}
                </p>
              )}
            </div>

            {completeMutation.isError && (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription className="text-sm">
                  {(completeMutation.error as Error)?.message ||
                    "Verification failed. Please try again."}
                </AlertDescription>
              </Alert>
            )}

            <button
              type="submit"
              className={cn(buttonVariants(), "w-full")}
              disabled={completeMutation.isPending}
            >
              {completeMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Verify &amp; Connect
            </button>

            <button
              type="button"
              className={cn(buttonVariants({ variant: "ghost" }), "w-full gap-2")}
              onClick={handleBack}
              disabled={completeMutation.isPending}
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </button>
          </form>
        ) : (
          /* Push notification — auto-triggered with countdown */
          <div className="space-y-4">
            {/* Countdown progress */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>Waiting for approval</span>
                <span className="tabular-nums font-medium">
                  {countdown > 0 ? `${countdown}s remaining` : "Time's up"}
                </span>
              </div>
              <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full transition-all duration-1000 ease-linear"
                  style={{ width: `${(countdown / PUSH_TIMEOUT_SECONDS) * 100}%` }}
                />
              </div>
            </div>

            {completeMutation.isError && (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription className="text-sm">
                  {(completeMutation.error as Error)?.message ||
                    "Approval was not received. Please try again."}
                </AlertDescription>
              </Alert>
            )}

            {!completeMutation.isError && (
              <button
                type="button"
                className={cn(buttonVariants(), "w-full")}
                disabled
              >
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Waiting for push approval...
              </button>
            )}

            <button
              type="button"
              className={cn(buttonVariants({ variant: "ghost" }), "w-full gap-2")}
              onClick={handleBack}
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </button>
          </div>
        )}
      </div>
    );
  }

  // ────────── Step 1: Credentials screen ──────────
  return (
    <div className="space-y-4">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          credentialsForm.handleSubmit(onSubmitCredentials)();
        }}
        className="space-y-4"
      >
        <div className="space-y-2">
          <Label htmlFor="rh-username">Robinhood Username / Email</Label>
          <Input
            id="rh-username"
            placeholder="your@email.com"
            autoComplete="username"
            {...credentialsForm.register("username")}
          />
          {credentialsForm.formState.errors.username && (
            <p className="text-xs text-destructive">
              {credentialsForm.formState.errors.username.message}
            </p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="rh-password">Password</Label>
          <Input
            id="rh-password"
            type="password"
            placeholder="••••••••"
            autoComplete="current-password"
            {...credentialsForm.register("password")}
          />
          {credentialsForm.formState.errors.password && (
            <p className="text-xs text-destructive">
              {credentialsForm.formState.errors.password.message}
            </p>
          )}
        </div>

        <div className="rounded-lg bg-muted/50 p-3 flex items-start gap-2">
          <Shield className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
          <div className="text-xs text-muted-foreground space-y-1">
            <p>
              Your credentials are used only for authentication and are never
              stored. Session tokens are encrypted at rest. If you have 2FA enabled, you will be prompted for verification in
              the next step.
            </p>
          </div>
        </div>

        {initiateMutation.isError && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription className="text-sm">
              {(initiateMutation.error as Error)?.message ||
                "Connection failed."}{" "}
              You can also try Plaid or CSV import.
            </AlertDescription>
          </Alert>
        )}

        <button
          type="submit"
          className={cn(buttonVariants(), "w-full")}
          disabled={initiateMutation.isPending}
        >
          {initiateMutation.isPending && (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          )}
          Connect Robinhood
        </button>
      </form>
    </div>
  );
}
