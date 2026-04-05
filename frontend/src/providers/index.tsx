"use client";
/**
 * App-wide providers: React Query, tooltips, toast.
 *
 * `QueryClient` is created once with `useState(lazy init)` so it is not recreated
 * on re-renders (important under the App Router). Defaults: `retry: 1` and
 * `refetchOnWindowFocus: false` for lighter, less noisy fetching.
 *
 * Added: 2026-04-03
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        {children}
        <Toaster position="top-right" richColors closeButton />
      </TooltipProvider>
    </QueryClientProvider>
  );
}
