"use client";

import { create } from "zustand";
import type { ChatMessage, ChatSession } from "./types";

interface ChatStore {
  sessions: ChatSession[];
  activeSessionId: string | null;
  messages: Record<string, ChatMessage[]>;

  createSession: () => string;
  setActiveSession: (id: string | null) => void;
  addMessage: (sessionId: string, message: ChatMessage) => void;
  deleteSession: (id: string) => void;
  renameSession: (id: string, title: string) => void;
  toggleStar: (id: string) => void;
  toggleArchive: (id: string) => void;
}

function generateId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export const useChatStore = create<ChatStore>((set) => ({
  sessions: [],
  activeSessionId: null,
  messages: {},

  createSession: () => {
    const id = generateId();
    const session: ChatSession = {
      id,
      title: "New chat",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      preview: "",
      starred: false,
      archived: false,
    };
    set((s) => ({
      sessions: [session, ...s.sessions],
      activeSessionId: id,
      messages: { ...s.messages, [id]: [] },
    }));
    return id;
  },

  setActiveSession: (id) => set({ activeSessionId: id }),

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

  deleteSession: (id) =>
    set((s) => {
      const { [id]: _, ...rest } = s.messages;
      return {
        sessions: s.sessions.filter((sess) => sess.id !== id),
        messages: rest,
        activeSessionId: s.activeSessionId === id ? null : s.activeSessionId,
      };
    }),

  renameSession: (id, title) =>
    set((s) => ({
      sessions: s.sessions.map((sess) =>
        sess.id === id ? { ...sess, title } : sess
      ),
    })),

  toggleStar: (id) =>
    set((s) => ({
      sessions: s.sessions.map((sess) =>
        sess.id === id ? { ...sess, starred: !sess.starred } : sess
      ),
    })),

  toggleArchive: (id) =>
    set((s) => ({
      sessions: s.sessions.map((sess) =>
        sess.id === id
          ? { ...sess, archived: !sess.archived }
          : sess
      ),
      activeSessionId:
        s.activeSessionId === id ? null : s.activeSessionId,
    })),
}));
