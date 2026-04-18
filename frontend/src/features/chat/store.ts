"use client";

/**
 * Server-backed chat store. Postgres is the source of truth; this mirrors
 * the authenticated user's sessions locally and lazily loads messages
 * per-session. Mutations apply optimistically with rollback on API error.
 */

import { create } from "zustand";
import {
  createChatSession,
  deleteChatSession,
  getChatSession,
  listChatSessions,
  updateChatSession,
} from "./api";
import type { ChatMessage, ChatSession } from "./types";

interface ChatStore {
  sessions: ChatSession[];
  activeSessionId: string | null;
  messages: Record<string, ChatMessage[]>;

  // User id the in-memory data belongs to (null = empty/unloaded). Lets
  // us detect same-tab user switches and refetch automatically.
  hydratedForUserId: string | null;
  // Session ids whose messages have already been fetched.
  loadedMessageIds: Set<string>;
  loadingSessions: boolean;
  loadingMessages: boolean;

  loadSessions: (userId: string) => Promise<void>;
  reset: () => void;
  createSession: () => Promise<string | null>;
  setActiveSession: (id: string | null) => Promise<void>;
  addMessage: (sessionId: string, message: ChatMessage) => void;
  appendToMessage: (sessionId: string, messageId: string, delta: string) => void;
  deleteSession: (id: string) => Promise<void>;
  renameSession: (id: string, title: string) => Promise<void>;
  toggleStar: (id: string) => Promise<void>;
  toggleArchive: (id: string) => Promise<void>;
}

const EMPTY_STATE = {
  sessions: [] as ChatSession[],
  activeSessionId: null as string | null,
  messages: {} as Record<string, ChatMessage[]>,
  hydratedForUserId: null as string | null,
  loadedMessageIds: new Set<string>(),
  loadingSessions: false,
  loadingMessages: false,
};

export const useChatStore = create<ChatStore>((set, get) => ({
  ...EMPTY_STATE,

  loadSessions: async (userId: string) => {
    const { loadingSessions, hydratedForUserId } = get();
    if (loadingSessions || hydratedForUserId === userId) return;

    set({ loadingSessions: true });
    try {
      const sessions = await listChatSessions();
      // Guard against a user switch mid-flight: only commit if we're still
      // hydrating for the same id (prevents cross-user leakage).
      const stillSame =
        get().hydratedForUserId === null ||
        get().hydratedForUserId === userId;
      if (!stillSame) return;
      set({
        sessions,
        hydratedForUserId: userId,
        loadingSessions: false,
      });
    } catch (err) {
      // Don't mark as hydrated on failure — a transient error would otherwise
      // lock the sidebar into "no conversations" for the store's lifetime.
      console.error("Failed to load chat sessions", err);
      set({ loadingSessions: false });
    }
  },

  reset: () => set(() => ({ ...EMPTY_STATE, loadedMessageIds: new Set() })),

  createSession: async () => {
    try {
      const session = await createChatSession();
      set((s) => ({
        sessions: [session, ...s.sessions],
        activeSessionId: session.id,
        messages: { ...s.messages, [session.id]: [] },
        // Mark empty session as loaded to skip a no-op GET on first use.
        loadedMessageIds: new Set(s.loadedMessageIds).add(session.id),
      }));
      return session.id;
    } catch (err) {
      console.error("Failed to create chat session", err);
      return null;
    }
  },

  setActiveSession: async (id) => {
    set({ activeSessionId: id });
    if (!id) return;

    const { loadedMessageIds, loadingMessages } = get();
    if (loadedMessageIds.has(id) || loadingMessages) return;

    set({ loadingMessages: true });
    try {
      const { session, messages } = await getChatSession(id);
      set((s) => ({
        // Merge latest session metadata (e.g. auto-derived title).
        sessions: s.sessions.map((sess) => (sess.id === id ? session : sess)),
        messages: { ...s.messages, [id]: messages },
        loadedMessageIds: new Set(s.loadedMessageIds).add(id),
        loadingMessages: false,
      }));
    } catch (err) {
      console.error("Failed to load session messages", err);
      set({ loadingMessages: false });
    }
  },

  addMessage: (sessionId, message) =>
    set((s) => {
      const existing = s.messages[sessionId] ?? [];
      const updated = [...existing, message];

      const sessions = s.sessions.map((sess) =>
        sess.id === sessionId
          ? {
              ...sess,
              preview: message.content.slice(0, 80),
              updated_at: new Date().toISOString(),
              title:
                sess.title === "New chat" && message.role === "user"
                  ? message.content.slice(0, 40)
                  : sess.title,
            }
          : sess
      );

      return { messages: { ...s.messages, [sessionId]: updated }, sessions };
    }),

  appendToMessage: (sessionId, messageId, delta) =>
    set((s) => {
      const msgs = s.messages[sessionId];
      if (!msgs) return s;

      let changed = false;
      const updatedMsgs = msgs.map((m) => {
        if (m.id !== messageId) return m;
        changed = true;
        return { ...m, content: m.content + delta };
      });
      if (!changed) return s;

      const last = updatedMsgs[updatedMsgs.length - 1];
      const sessions = s.sessions.map((sess) =>
        sess.id === sessionId
          ? {
              ...sess,
              preview: last.content.slice(0, 80),
              updated_at: new Date().toISOString(),
            }
          : sess,
      );

      return {
        messages: { ...s.messages, [sessionId]: updatedMsgs },
        sessions,
      };
    }),

  deleteSession: async (id) => {
    const prev = get();
    set((s) => {
      const { [id]: _removed, ...restMessages } = s.messages;
      const nextLoaded = new Set(s.loadedMessageIds);
      nextLoaded.delete(id);
      return {
        sessions: s.sessions.filter((sess) => sess.id !== id),
        messages: restMessages,
        activeSessionId: s.activeSessionId === id ? null : s.activeSessionId,
        loadedMessageIds: nextLoaded,
      };
    });
    try {
      await deleteChatSession(id);
    } catch (err) {
      console.error("Failed to delete chat session", err);
      set({
        sessions: prev.sessions,
        messages: prev.messages,
        activeSessionId: prev.activeSessionId,
        loadedMessageIds: prev.loadedMessageIds,
      });
    }
  },

  renameSession: async (id, title) => {
    const prev = get().sessions;
    set((s) => ({
      sessions: s.sessions.map((sess) =>
        sess.id === id ? { ...sess, title } : sess,
      ),
    }));
    try {
      await updateChatSession(id, { title });
    } catch (err) {
      console.error("Failed to rename chat session", err);
      set({ sessions: prev });
    }
  },

  toggleStar: async (id) => {
    const prev = get().sessions;
    const next = prev.map((sess) =>
      sess.id === id ? { ...sess, starred: !sess.starred } : sess,
    );
    const target = next.find((s) => s.id === id);
    set({ sessions: next });
    if (!target) return;
    try {
      await updateChatSession(id, { starred: target.starred });
    } catch (err) {
      console.error("Failed to toggle star", err);
      set({ sessions: prev });
    }
  },

  toggleArchive: async (id) => {
    const prev = get();
    const prevSessions = prev.sessions;
    const next = prevSessions.map((sess) =>
      sess.id === id ? { ...sess, archived: !sess.archived } : sess,
    );
    const target = next.find((s) => s.id === id);
    set({
      sessions: next,
      // Archiving the active session clears it so the welcome screen shows.
      activeSessionId:
        prev.activeSessionId === id ? null : prev.activeSessionId,
    });
    if (!target) return;
    try {
      await updateChatSession(id, { archived: target.archived });
    } catch (err) {
      console.error("Failed to toggle archive", err);
      set({
        sessions: prevSessions,
        activeSessionId: prev.activeSessionId,
      });
    }
  },
}));
