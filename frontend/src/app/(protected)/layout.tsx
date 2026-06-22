"use client";
import { SidebarNav } from "@/components/layout/sidebar-nav";
import { Topbar } from "@/components/layout/topbar";
import { AuthGuard } from "@/components/layout/auth-guard";
import { ChatHydrator } from "@/features/chat/chat-hydrator";
import { DataPrefetcher } from "@/components/layout/data-prefetcher";
import { FloatingAssistantWidget } from "@/features/chat/floating-assistant-widget";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const fullBleed = pathname.startsWith("/assistant");

  // App shell intentionally has NO max-width on its content well  -  the same
  // pattern Linear, Vercel, GitHub, Notion, and Robinhood web all use for
  // dashboards. Internal grids/cards spread to fill the viewport. Only padding
  // scales. Capping here was the root cause of "concentrated in the center"
  // gutters on ultrawide / curved monitors at any DPI scale.
  return (
    <AuthGuard>
      <ChatHydrator />
      <DataPrefetcher />
      <FloatingAssistantWidget />
      <div className="flex h-screen overflow-hidden">
        <SidebarNav />
        <div className="flex-1 flex flex-col min-w-0 relative">
          <Topbar />
          <main
            className={cn(
              "flex-1 min-h-0 overflow-y-auto overflow-x-hidden",
              fullBleed
                ? "p-0"
                : "w-full px-3 py-4 sm:px-4 sm:py-5 md:px-6 md:py-6 lg:px-8 lg:py-7 xl:px-10 xl:py-8 2xl:px-12",
            )}
          >
            {children}
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
