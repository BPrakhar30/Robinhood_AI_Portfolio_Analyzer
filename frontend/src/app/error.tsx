"use client";

import { useEffect } from "react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Unhandled error:", error.digest || error.message);
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="text-center space-y-4">
        <h1 className="text-6xl font-bold text-muted-foreground">500</h1>
        <h2 className="text-xl font-semibold text-foreground">
          Something went wrong
        </h2>
        <p className="text-muted-foreground max-w-md">
          An unexpected error occurred. Please try again or return to the
          dashboard.
        </p>
        <div className="flex gap-3 justify-center mt-4">
          <button
            onClick={reset}
            className="px-6 py-2 rounded-md bg-amber-600 text-white font-medium hover:bg-amber-700 transition-colors"
          >
            Try again
          </button>
          <a
            href="/dashboard"
            className="px-6 py-2 rounded-md border border-border text-foreground font-medium hover:bg-muted transition-colors"
          >
            Dashboard
          </a>
        </div>
      </div>
    </div>
  );
}
