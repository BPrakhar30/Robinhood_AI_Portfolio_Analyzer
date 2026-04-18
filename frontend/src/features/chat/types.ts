export interface ChatMessage {
  // String for uniform keying: server id for persisted, temp id for streaming.
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  toolsUsed?: string[];
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  preview: string;
  starred: boolean;
  archived: boolean;
}
