import { API_BASE_URL, api, getAccessToken } from "@/lib/api/client";
import type { ChatMessage, ChatSession } from "./types";

// ─────────────────────── Assistant (stream & ask) ───────────────────────

export interface AssistantAnswer {
  answer: string;
  tools_used: string[];
}

export async function askAssistant(question: string): Promise<AssistantAnswer> {
  return api.post<AssistantAnswer>("/api/v1/assistant/ask", { question });
}

export interface StreamHandlers {
  onDelta: (text: string) => void;
  onDone: (toolsUsed: string[]) => void;
  onError: (message: string) => void;
}

/**
 * Stream an assistant answer via POST + SSE (hand-rolled because ``EventSource``
 * is GET-only and can't send auth headers or a JSON body).
 *
 * With ``sessionId`` the backend persists turns and replays history; without
 * it the stream is ephemeral.
 */
export async function streamAssistant(
  question: string,
  handlers: StreamHandlers,
  options: { sessionId?: string; signal?: AbortSignal } = {},
): Promise<void> {
  const token = getAccessToken();
  const { sessionId, signal } = options;

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}/api/v1/assistant/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        question,
        ...(sessionId ? { session_id: sessionId } : {}),
      }),
      signal,
    });
  } catch (err) {
    if ((err as { name?: string })?.name === "AbortError") return;
    handlers.onError("Network error while reaching the assistant.");
    return;
  }

  if (!res.ok || !res.body) {
    handlers.onError(
      res.status === 401
        ? "Your session has expired. Please log in again."
        : `Assistant request failed (${res.status}).`,
    );
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let done = false;

  try {
    while (!done) {
      const { value, done: streamDone } = await reader.read();
      if (streamDone) break;

      buffer += decoder.decode(value, { stream: true });

      // SSE frames are blank-line delimited; keep the trailing partial.
      let sepIdx = buffer.indexOf("\n\n");
      while (sepIdx !== -1) {
        const frame = buffer.slice(0, sepIdx);
        buffer = buffer.slice(sepIdx + 2);

        let eventName = "message";
        let dataLine = "";
        for (const line of frame.split("\n")) {
          if (line.startsWith("event:")) {
            eventName = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            dataLine += line.slice(5).trim();
          }
        }

        if (dataLine) {
          try {
            const parsed = JSON.parse(dataLine) as {
              type?: string;
              text?: string;
              tools_used?: string[];
              message?: string;
            };
            if (eventName === "delta" && typeof parsed.text === "string") {
              handlers.onDelta(parsed.text);
            } else if (eventName === "done") {
              handlers.onDone(parsed.tools_used ?? []);
              done = true;
              break;
            } else if (eventName === "error") {
              handlers.onError(parsed.message ?? "Assistant error.");
              done = true;
              break;
            }
          } catch {
            // Ignore malformed frame; stream may still recover.
          }
        }

        sepIdx = buffer.indexOf("\n\n");
      }
    }
  } catch (err) {
    if ((err as { name?: string })?.name === "AbortError") return;
    handlers.onError("Stream interrupted.");
  } finally {
    try {
      reader.releaseLock();
    } catch {
      /* noop */
    }
  }
}

// ─────────────────────── Chat sessions (REST CRUD) ───────────────────────

interface ChatSessionDTO {
  id: string;
  title: string;
  starred: boolean;
  archived: boolean;
  preview: string;
  created_at: string;
  updated_at: string;
}

interface ChatMessageDTO {
  id: number;
  role: "user" | "assistant";
  content: string;
  tools_used: string[] | null;
  created_at: string;
}

interface ChatSessionDetailDTO extends ChatSessionDTO {
  messages: ChatMessageDTO[];
}

function toSession(dto: ChatSessionDTO): ChatSession {
  return {
    id: dto.id,
    title: dto.title,
    starred: dto.starred,
    archived: dto.archived,
    preview: dto.preview ?? "",
    created_at: dto.created_at,
    updated_at: dto.updated_at,
  };
}

function toMessage(dto: ChatMessageDTO): ChatMessage {
  return {
    id: String(dto.id),
    role: dto.role,
    content: dto.content,
    timestamp: dto.created_at,
    toolsUsed: dto.tools_used ?? undefined,
  };
}

export async function listChatSessions(): Promise<ChatSession[]> {
  const raw = await api.get<ChatSessionDTO[]>("/api/v1/chat/sessions");
  return raw.map(toSession);
}

export async function createChatSession(title?: string): Promise<ChatSession> {
  const raw = await api.post<ChatSessionDTO>("/api/v1/chat/sessions", {
    title: title ?? null,
  });
  return toSession(raw);
}

export async function getChatSession(
  id: string,
): Promise<{ session: ChatSession; messages: ChatMessage[] }> {
  const raw = await api.get<ChatSessionDetailDTO>(
    `/api/v1/chat/sessions/${id}`,
  );
  return {
    session: toSession(raw),
    messages: raw.messages.map(toMessage),
  };
}

export async function updateChatSession(
  id: string,
  patch: { title?: string; starred?: boolean; archived?: boolean },
): Promise<ChatSession> {
  const raw = await api.patch<ChatSessionDTO>(
    `/api/v1/chat/sessions/${id}`,
    patch,
  );
  return toSession(raw);
}

export async function deleteChatSession(id: string): Promise<void> {
  await api.delete<void>(`/api/v1/chat/sessions/${id}`);
}

export async function truncateChatMessages(
  id: string,
  fromIndex: number,
): Promise<ChatMessage[]> {
  const raw = await api.post<ChatMessageDTO[]>(
    `/api/v1/chat/sessions/${id}/messages/truncate`,
    { from_index: fromIndex },
  );
  return raw.map(toMessage);
}
