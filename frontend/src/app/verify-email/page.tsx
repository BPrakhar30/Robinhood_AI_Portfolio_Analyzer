"use client";
/**
 * Email OTP entry: six single-digit inputs. Auto-submits when all cells are filled;
 * paste on the row fills digits and submits if the paste is six digits. `email`
 * comes from `?email=` (set by register/login resend flows).
 *
 * Added: 2026-04-03
 */
import { Suspense, useRef, useState, useCallback } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Mail, Loader2, ArrowLeft } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useVerifyEmail, useResendVerification } from "@/features/auth/hooks";

const CODE_LENGTH = 6;

export default function VerifyEmailPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      }
    >
      <VerifyEmailContent />
    </Suspense>
  );
}

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const email = searchParams.get("email") || "";

  const verifyMutation = useVerifyEmail();
  const resendMutation = useResendVerification();

  const [digits, setDigits] = useState<string[]>(Array(CODE_LENGTH).fill(""));
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  const handleChange = useCallback(
    (index: number, value: string) => {
      if (!/^\d*$/.test(value)) return;

      const char = value.slice(-1);
      const next = [...digits];
      next[index] = char;
      setDigits(next);

      if (char && index < CODE_LENGTH - 1) {
        inputRefs.current[index + 1]?.focus();
      }

      if (next.every((d) => d !== "") && next.join("").length === CODE_LENGTH) {
        verifyMutation.mutate({ email, code: next.join("") });
      }
    },
    [digits, email, verifyMutation]
  );

  const handleKeyDown = useCallback(
    (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Backspace" && !digits[index] && index > 0) {
        inputRefs.current[index - 1]?.focus();
      }
    },
    [digits]
  );

  const handlePaste = useCallback(
    (e: React.ClipboardEvent) => {
      e.preventDefault();
      const pasted = e.clipboardData
        .getData("text")
        .replace(/\D/g, "")
        .slice(0, CODE_LENGTH);
      if (!pasted) return;

      const next = Array(CODE_LENGTH).fill("");
      for (let i = 0; i < pasted.length; i++) {
        next[i] = pasted[i];
      }
      setDigits(next);

      const focusIndex = Math.min(pasted.length, CODE_LENGTH - 1);
      inputRefs.current[focusIndex]?.focus();

      if (pasted.length === CODE_LENGTH) {
        verifyMutation.mutate({ email, code: pasted });
      }
    },
    [email, verifyMutation]
  );

  const handleSubmit = () => {
    const code = digits.join("");
    if (code.length === CODE_LENGTH) {
      verifyMutation.mutate({ email, code });
    }
  };

  if (!email) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4 bg-muted/30">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6 text-center space-y-4">
            <p className="text-sm text-muted-foreground">
              Missing email address. Please register again.
            </p>
            <Link href="/register" className={cn(buttonVariants(), "w-full")}>
              Go to registration
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-muted/30">
      <div className="w-full max-w-md space-y-6">
        <div className="flex flex-col items-center space-y-4">
          <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
            <Mail className="h-8 w-8 text-primary" />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Check your email
          </h1>
          <p className="text-sm text-muted-foreground text-center max-w-xs">
            We sent a 6-digit verification code to{" "}
            <span className="font-medium text-foreground">{email}</span>
          </p>
        </div>

        <Card>
          <CardContent className="pt-6 space-y-6">
            <div className="space-y-2">
              <p className="text-sm font-medium text-center">
                Enter verification code
              </p>
              {/* Paste targets the container so one gesture fills all inputs (see handlePaste). */}
              <div
                className="flex justify-center gap-2"
                onPaste={handlePaste}
              >
                {Array.from({ length: CODE_LENGTH }).map((_, i) => (
                  <Input
                    key={i}
                    ref={(el) => { inputRefs.current[i] = el; }}
                    type="text"
                    inputMode="numeric"
                    maxLength={1}
                    value={digits[i]}
                    onChange={(e) => handleChange(i, e.target.value)}
                    onKeyDown={(e) => handleKeyDown(i, e)}
                    className="w-12 h-14 text-center text-xl font-semibold"
                    autoFocus={i === 0}
                    disabled={verifyMutation.isPending}
                  />
                ))}
              </div>
            </div>

            {verifyMutation.isError && (
              <Alert variant="destructive">
                <AlertDescription className="text-sm">
                  {(verifyMutation.error as Error)?.message ||
                    "Invalid code. Please try again."}
                </AlertDescription>
              </Alert>
            )}

            <button
              className={cn(buttonVariants(), "w-full")}
              disabled={
                digits.join("").length < CODE_LENGTH ||
                verifyMutation.isPending
              }
              onClick={handleSubmit}
            >
              {verifyMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Verify email
            </button>

            <div className="text-center space-y-3">
              <p className="text-xs text-muted-foreground">
                Didn&apos;t receive the code? Check your spam folder.
              </p>
              <button
                className="text-sm font-medium text-foreground hover:underline disabled:opacity-50 cursor-pointer"
                disabled={resendMutation.isPending}
                onClick={() => resendMutation.mutate(email)}
              >
                {resendMutation.isPending
                  ? "Sending..."
                  : "Resend code"}
              </button>
            </div>
          </CardContent>
        </Card>

        <Link
          href="/login"
          className={cn(
            buttonVariants({ variant: "ghost" }),
            "w-full gap-2"
          )}
        >
          <ArrowLeft className="h-4 w-4" />
          Back to sign in
        </Link>
      </div>
    </div>
  );
}
