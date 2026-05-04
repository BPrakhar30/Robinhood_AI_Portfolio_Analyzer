"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
  type KeyboardEvent,
  type PointerEvent,
} from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bot,
  ExternalLink,
  Grip,
  Info,
  Loader2,
  MessageCircle,
  Plus,
  Send,
  Sparkles,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { streamAssistant } from "@/features/chat/api";
import { getChatSuggestions } from "@/features/chat/chat-suggestions";
import { GenerationStageIndicator } from "@/features/chat/generation-stage-indicator";
import { MarkdownMessage } from "@/features/chat/markdown-message";
import { useChatStore } from "@/features/chat/store";
import type { ChatMessage } from "@/features/chat/types";

const POSITION_KEY = "portfolio-copilot-floating-position";
const EMPTY_MESSAGES: ChatMessage[] = [];

type WidgetPosition = {
  x: number;
  y: number;
};

function generateId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function clampPosition(pos: WidgetPosition): WidgetPosition {
  if (typeof window === "undefined") return pos;
  const margin = 12;
  const size = 64;
  return {
    x: Math.min(Math.max(pos.x, margin), window.innerWidth - size - margin),
    y: Math.min(Math.max(pos.y, margin), window.innerHeight - size - margin),
  };
}

function defaultPosition(): WidgetPosition {
  if (typeof window === "undefined") return { x: 0, y: 0 };
  return {
    x: window.innerWidth - 88,
    y: window.innerHeight - 112,
  };
}

function initialPosition(): WidgetPosition {
  if (typeof window === "undefined") return defaultPosition();
  try {
    const saved = window.localStorage.getItem(POSITION_KEY);
    return clampPosition(saved ? JSON.parse(saved) : defaultPosition());
  } catch {
    return clampPosition(defaultPosition());
  }
}

export function FloatingAssistantWidget() {
  const pathname = usePathname();
  const {
    activeSessionId,
    messages,
    createSession,
    setActiveSession,
    addMessage,
    appendToMessage,
  } = useChatStore();

  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [position, setPosition] = useState<WidgetPosition>(() => initialPosition());
  const [isDragging, setIsDragging] = useState(false);
  const isClient = useSyncExternalStore(
    () => () => undefined,
    () => true,
    () => false,
  );

  const dragRef = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    offsetX: number;
    offsetY: number;
    moved: boolean;
    latest: WidgetPosition;
  } | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const activeMessages = activeSessionId
    ? messages[activeSessionId] ?? EMPTY_MESSAGES
    : EMPTY_MESSAGES;
  const suggestions = useMemo(
    () => getChatSuggestions(pathname, activeMessages, 2),
    [pathname, activeMessages],
  );
  const latestUserQuestion =
    [...activeMessages].reverse().find((m) => m.role === "user")?.content ?? "";

  useEffect(() => {
    const handleResize = () => setPosition((prev) => clampPosition(prev));
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeMessages.length, isTyping, open]);

  useEffect(() => {
    if (open) {
      window.setTimeout(() => textareaRef.current?.focus(), 80);
    }
  }, [open]);

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  const persistPosition = useCallback((next: WidgetPosition) => {
    const clamped = clampPosition(next);
    setPosition(clamped);
    try {
      window.localStorage.setItem(POSITION_KEY, JSON.stringify(clamped));
    } catch {
      /* localStorage may be unavailable in private contexts */
    }
  }, []);

  const handlePointerDown = (event: PointerEvent<HTMLButtonElement>) => {
    if (open) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      offsetX: event.clientX - position.x,
      offsetY: event.clientY - position.y,
      moved: false,
      latest: position,
    };
    setIsDragging(true);
  };

  const handlePointerMove = (event: PointerEvent<HTMLButtonElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    const next = clampPosition({
      x: event.clientX - drag.offsetX,
      y: event.clientY - drag.offsetY,
    });
    drag.latest = next;
    if (Math.abs(event.clientX - drag.startX) > 4 || Math.abs(event.clientY - drag.startY) > 4) {
      drag.moved = true;
    }
    setPosition(next);
  };

  const handlePointerUp = (event: PointerEvent<HTMLButtonElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    event.currentTarget.releasePointerCapture(event.pointerId);
    dragRef.current = null;
    setIsDragging(false);
    persistPosition(drag.latest);
    if (!drag.moved) {
      setOpen(true);
    }
  };

  const sendTurn = useCallback(
    async (content: string, sid: string) => {
      const userMsg: ChatMessage = {
        id: generateId(),
        role: "user",
        content,
        timestamp: new Date().toISOString(),
      };
      const assistantId = generateId();
      const assistantMsg: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        timestamp: new Date().toISOString(),
      };

      addMessage(sid, userMsg);
      addMessage(sid, assistantMsg);
      setInput("");
      setIsTyping(true);

      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      await streamAssistant(
        content,
        {
          onDelta: (delta) => appendToMessage(sid, assistantId, delta),
          onDone: () => {
            setIsTyping(false);
            abortRef.current = null;
          },
          onError: (message) => {
            appendToMessage(sid, assistantId, `\n\n_${message}_`);
            setIsTyping(false);
            abortRef.current = null;
          },
        },
        { sessionId: sid, signal: controller.signal },
      );
    },
    [addMessage, appendToMessage],
  );

  const handleSend = useCallback(
    async (text?: string) => {
      const content = (text ?? input).trim();
      if (!content || isTyping) return;

      let sid = activeSessionId;
      if (!sid) {
        sid = await createSession();
        if (!sid) return;
      }
      await sendTurn(content, sid);
    },
    [activeSessionId, createSession, input, isTyping, sendTurn],
  );

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  const handleNewChat = () => {
    abortRef.current?.abort();
    setInput("");
    setIsTyping(false);
    setActiveSession(null);
  };

  if (!isClient || pathname.startsWith("/assistant")) {
    return null;
  }

  return (
    <>
      {open && (
        <div className="fixed bottom-5 right-6 z-50 flex h-[min(calc(100vh-2.5rem),44rem)] w-[min(calc(100vw-2rem),26rem)] flex-col overflow-hidden rounded-2xl border border-border/80 bg-background/95 shadow-2xl backdrop-blur supports-[backdrop-filter]:bg-background/90">
          <div className="shrink-0 flex items-center justify-between border-b border-border/70 bg-muted/30 px-4 py-3">
            <div className="flex items-center gap-2">
              <div className="rounded-xl bg-amber-500/15 p-2">
                <Sparkles className="h-4 w-4 text-amber-600 dark:text-amber-400" />
              </div>
              <div>
                <p className="text-sm font-semibold">Portfolio Copilot</p>
                <p className="text-[11px] text-muted-foreground">
                  Ask about this page or your holdings
                </p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={handleNewChat}
                aria-label="Start new chat"
              >
                <Plus className="h-4 w-4" />
              </Button>
              <Link
                href="/assistant"
                aria-label="Open full assistant"
                className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
              >
                <ExternalLink className="h-4 w-4" />
              </Link>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => setOpen(false)}
                aria-label="Close assistant"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>

          <div className="assistant-widget-scroll min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-4 py-3">
            {activeMessages.length === 0 ? (
              <div className="space-y-3 py-2">
                <div className="rounded-2xl border border-amber-500/20 bg-amber-500/5 p-3">
                  <div className="mb-1 flex items-center gap-2 text-sm font-medium">
                    <Bot className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                    Start with context
                  </div>
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    I can combine the page you are viewing with your portfolio data,
                    holdings, returns, risk alerts, stock data, and macro signals.
                  </p>
                </div>
                <div className="grid gap-2">
                  {suggestions.map((suggestion) => (
                    <button
                      key={suggestion}
                      type="button"
                      onClick={() => handleSend(suggestion)}
                      className="rounded-xl border border-border bg-card px-3 py-2 text-left text-xs leading-relaxed transition-colors hover:border-amber-500/50 hover:bg-amber-500/5"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {activeMessages.map((message) => (
                  <div
                    key={message.id}
                    className={cn(
                      "flex",
                      message.role === "user" ? "justify-end" : "justify-start",
                    )}
                  >
                    <div
                      className={cn(
                        "min-w-0 max-w-[90%] overflow-hidden break-words rounded-2xl px-3 py-2 text-sm",
                        message.role === "user"
                          ? "bg-primary text-primary-foreground"
                          : "border border-border/70 bg-muted/40",
                      )}
                    >
                      {message.role === "assistant" ? (
                        message.content ? (
                          <MarkdownMessage content={message.content} onSend={handleSend} />
                        ) : (
                          <GenerationStageIndicator
                            key={latestUserQuestion}
                            question={latestUserQuestion}
                          />
                        )
                      ) : (
                        <p className="whitespace-pre-wrap leading-relaxed">
                          {message.content}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
                {!isTyping && activeMessages.some((m) => m.role === "assistant" && m.content.trim()) && (
                  <div className="ml-1 space-y-1.5 pt-1">
                    <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/70">
                      Suggested next
                    </p>
                    <div className="grid gap-1.5">
                      {suggestions.map((suggestion) => (
                        <button
                          key={suggestion}
                          type="button"
                          onClick={() => handleSend(suggestion)}
                          className="rounded-xl border border-border/80 bg-background px-3 py-2 text-left text-[11px] leading-snug text-muted-foreground transition-colors hover:border-amber-500/50 hover:bg-amber-500/5 hover:text-foreground"
                        >
                          {suggestion}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                <div ref={bottomRef} />
              </div>
            )}
          </div>

          <div className="shrink-0 border-t border-border/70 p-3">
            <div className="flex items-end gap-2">
              <Textarea
                ref={textareaRef}
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about your portfolio..."
                className="max-h-28 min-h-10 resize-none rounded-xl text-sm"
                disabled={isTyping}
              />
              <Button
                size="icon"
                className="h-10 w-10 shrink-0 bg-amber-600 text-white hover:bg-amber-700"
                onClick={() => handleSend()}
                disabled={!input.trim() || isTyping}
                aria-label="Send message"
              >
                {isTyping ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
            <div className="flex items-center justify-center gap-1 pt-1.5">
              <Info className="h-2.5 w-2.5 text-amber-600/50 dark:text-amber-400/50 shrink-0" />
              <p className="text-[9px] text-muted-foreground/50">
                AI-generated analysis. Not financial advice.
              </p>
            </div>
          </div>
        </div>
      )}

      {!open && (
        <button
          type="button"
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          className={cn(
            "fixed z-50 flex h-14 w-14 items-center justify-center rounded-full border border-amber-500/30 bg-background shadow-xl ring-1 ring-black/5 transition-transform hover:scale-105",
            "before:absolute before:inset-0 before:rounded-full before:bg-amber-500/10 before:content-['']",
            isDragging ? "cursor-grabbing scale-105" : "cursor-grab",
          )}
          style={{ left: position.x, top: position.y, touchAction: "none" }}
          aria-label="Open portfolio copilot"
        >
          <MessageCircle className="relative h-6 w-6 text-amber-600 dark:text-amber-400" />
          <Grip className="absolute -right-1 -top-1 h-4 w-4 rounded-full bg-background p-0.5 text-muted-foreground shadow" />
        </button>
      )}
    </>
  );
}
