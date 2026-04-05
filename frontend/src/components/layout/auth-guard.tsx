"use client";
/**
 * Wraps protected app routes: shows a skeleton until auth is known, then renders
 * children or redirects to login.
 *
 * Waits on both Zustand (`isLoading`) and the `useCurrentUser` query so a hard
 * refresh does not redirect before `/auth/me` finishes.
 *
 * Added: 2026-04-03
 */
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/features/auth/store";
import { useCurrentUser } from "@/features/auth/hooks";
import { Skeleton } from "@/components/ui/skeleton";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuthStore();
  const { isLoading: isQueryLoading } = useCurrentUser();

  useEffect(() => {
    if (!isLoading && !isQueryLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isAuthenticated, isLoading, isQueryLoading, router]);

  if (isLoading || isQueryLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="space-y-4 w-full max-w-md px-4">
          <Skeleton className="h-8 w-48 mx-auto" />
          <Skeleton className="h-4 w-64 mx-auto" />
          <div className="space-y-2 mt-8">
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) return null;

  return <>{children}</>;
}
