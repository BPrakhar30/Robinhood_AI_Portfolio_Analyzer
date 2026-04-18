"use client";
import { SidebarNav } from "@/components/layout/sidebar-nav";
import { Topbar } from "@/components/layout/topbar";
import { AuthGuard } from "@/components/layout/auth-guard";
import { ChatHydrator } from "@/features/chat/chat-hydrator";

export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      {/* Hydrate chat on sign-in so the sidebar is ready before /assistant. */}
      <ChatHydrator />
      <div className="flex h-screen overflow-hidden">
        <SidebarNav />
        <div className="flex-1 flex flex-col min-w-0 relative">
          <Topbar />
          <main className="flex-1 min-h-0 p-4 md:p-6 lg:p-8 overflow-y-auto">
            {children}
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
