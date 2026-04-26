"use client";

/**
 * Keeps the chat store in sync with the authenticated user.
 *
 * Mounted once in the protected layout. Fetches sessions on sign-in and
 * wipes the store on logout / same-tab user switches. Renders nothing.
 */

import { useEffect } from "react";
import { useAuthStore } from "@/features/auth/store";
import { useChatStore } from "./store";

export function ChatHydrator() {
  const userId = useAuthStore((s) => (
    s.user?.id != null ? String(s.user.id) : null
  ));
  const loadSessions = useChatStore((s) => s.loadSessions);
  const reset = useChatStore((s) => s.reset);
  const hydratedForUserId = useChatStore((s) => s.hydratedForUserId);

  useEffect(() => {
    if (!userId) {
      if (hydratedForUserId !== null) reset();
      return;
    }
    if (hydratedForUserId !== userId) {
      void loadSessions(userId);
    }
  }, [userId, hydratedForUserId, loadSessions, reset]);

  return null;
}
