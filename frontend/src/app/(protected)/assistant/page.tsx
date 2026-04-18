"use client";

import { useRef, useEffect, useState, type KeyboardEvent } from "react";
import {
  Send,
  Mic,
  Bot,
  User,
  Sparkles,
  TrendingUp,
  ShieldAlert,
  BarChart3,
  Lightbulb,
  PanelLeftOpen,
  Plus,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { ChatSidebar } from "@/features/chat/chat-sidebar";
import { useChatStore } from "@/features/chat/store";
import type { ChatMessage } from "@/features/chat/types";
import { streamAssistant } from "@/features/chat/api";
import { MarkdownMessage } from "@/features/chat/markdown-message";

const SUGGESTIONS = [
  {
    icon: TrendingUp,
    label: "Which stock is hurting my returns most?",
  },
  {
    icon: ShieldAlert,
    label: "Show diversification issues",
  },
  {
    icon: BarChart3,
    label: "Compare my portfolio vs S&P 500",
  },
  {
    icon: Lightbulb,
    label: "Explain why my returns lag Nasdaq",
  },
];

function generateId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export default function AssistantPage() {
  const {
    activeSessionId,
    messages,
    createSession,
    addMessage,
    appendToMessage,
  } = useChatStore();

  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  // Track the in-flight stream so a new question / unmount cancels it.
  const abortRef = useRef<AbortController | null>(null);

  const activeMessages = activeSessionId ? messages[activeSessionId] ?? [] : [];
  const isWelcome = activeMessages.length === 0;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeMessages.length, isTyping]);

  useEffect(() => {
    textareaRef.current?.focus();
  }, [activeSessionId, isWelcome]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const handleSend = async (text?: string) => {
    const content = (text ?? input).trim();
    if (!content || isTyping) return;

    // Need a server-backed session id so the backend can persist the turn
    // and replay history on subsequent turns.
    let sid = activeSessionId;
    if (!sid) {
      sid = await createSession();
      if (!sid) return;
    }

    addMessage(sid, {
      id: generateId(),
      role: "user",
      content,
      timestamp: new Date().toISOString(),
    });
    setInput("");
    setIsTyping(true);

    // Empty assistant placeholder; stream deltas append into it.
    const assistantId = generateId();
    addMessage(sid, {
      id: assistantId,
      role: "assistant",
      content: "",
      timestamp: new Date().toISOString(),
    });

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
          // Surface the error inline so any partial answer stays visible.
          appendToMessage(sid, assistantId, `\n\n_${message}_`);
          setIsTyping(false);
          abortRef.current = null;
        },
      },
      { sessionId: sid, signal: controller.signal },
    );
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex absolute inset-0">
      {sidebarOpen && <ChatSidebar onClose={() => setSidebarOpen(false)} />}

      <div className="flex-1 flex flex-col min-w-0 h-full pt-14 bg-background z-30">
        {!sidebarOpen && (
          <div className="absolute top-[4.25rem] left-2 z-10 flex flex-col gap-1">
            <Tooltip>
              <TooltipTrigger
                className="inline-flex items-center justify-center h-9 w-9 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors cursor-pointer"
                onClick={() => setSidebarOpen(true)}
              >
                <PanelLeftOpen className="h-4 w-4" />
              </TooltipTrigger>
              <TooltipContent side="right">Open sidebar</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger
                className="inline-flex items-center justify-center h-9 w-9 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors cursor-pointer"
                onClick={() => {
                  createSession();
                }}
              >
                <Plus className="h-4 w-4" />
              </TooltipTrigger>
              <TooltipContent side="right">New chat</TooltipContent>
            </Tooltip>
          </div>
        )}

        {isWelcome ? (
          <div className="flex-1 flex flex-col items-center justify-center px-4">
            <div className="w-full max-w-2xl space-y-8">
              <div className="text-center space-y-3">
                <div className="h-14 w-14 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto">
                  <Sparkles className="h-7 w-7 text-primary" />
                </div>
                <h1 className="text-2xl font-semibold tracking-tight">
                  What would you like to know?
                </h1>
                <p className="text-sm text-muted-foreground max-w-sm mx-auto">
                  I have full context of your portfolio — ask away.
                </p>
              </div>

              <div className="rounded-xl border border-border/60 bg-background shadow-sm">
                <div className="relative">
                  <Textarea
                    ref={textareaRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask about your portfolio..."
                    rows={1}
                    className="resize-none pr-24 !min-h-[44px] max-h-32 rounded-xl border-0 bg-transparent shadow-none focus-visible:ring-0 text-sm py-2.5"
                  />
                  <div className="absolute right-2 bottom-1.5 flex items-center gap-1">
                    <Tooltip>
                      <TooltipTrigger
                        className="inline-flex items-center justify-center h-8 w-8 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors cursor-pointer"
                      >
                        <Mic className="h-4 w-4" />
                      </TooltipTrigger>
                      <TooltipContent>Use voice mode</TooltipContent>
                    </Tooltip>
                    <Button
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => handleSend()}
                      disabled={!input.trim()}
                    >
                      <Send className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s.label}
                    type="button"
                    onClick={() => handleSend(s.label)}
                    className="flex items-center gap-3 px-4 py-3 rounded-xl border border-border/60 bg-background text-sm text-left hover:bg-accent/50 hover:border-border transition-colors cursor-pointer group"
                  >
                    <s.icon className="h-4 w-4 text-muted-foreground group-hover:text-primary shrink-0 transition-colors" />
                    <span className="text-muted-foreground group-hover:text-foreground transition-colors">
                      {s.label}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-y-auto">
              <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
                {activeMessages.map((msg) => (
                  <div
                    key={msg.id}
                    className={cn(
                      "flex gap-3",
                      msg.role === "user" ? "justify-end" : "justify-start"
                    )}
                  >
                    {msg.role === "assistant" && (
                      <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                        <Bot className="h-4 w-4 text-primary" />
                      </div>
                    )}
                    <div
                      className={cn(
                        "rounded-2xl px-4 py-3 text-sm leading-relaxed max-w-[80%]",
                        msg.role === "user"
                          ? "bg-primary text-primary-foreground rounded-br-md whitespace-pre-wrap"
                          : "bg-muted rounded-bl-md"
                      )}
                    >
                      {msg.role === "assistant" ? (
                        msg.content ? (
                          <MarkdownMessage content={msg.content} />
                        ) : (
                          <div className="flex gap-1 py-1">
                            <span className="h-2 w-2 rounded-full bg-muted-foreground/40 animate-bounce [animation-delay:0ms]" />
                            <span className="h-2 w-2 rounded-full bg-muted-foreground/40 animate-bounce [animation-delay:150ms]" />
                            <span className="h-2 w-2 rounded-full bg-muted-foreground/40 animate-bounce [animation-delay:300ms]" />
                          </div>
                        )
                      ) : (
                        msg.content
                      )}
                    </div>
                    {msg.role === "user" && (
                      <div className="h-8 w-8 rounded-lg bg-muted flex items-center justify-center shrink-0 mt-0.5">
                        <User className="h-4 w-4 text-muted-foreground" />
                      </div>
                    )}
                  </div>
                ))}

                <div ref={bottomRef} />
              </div>
            </div>

            <div className="border-t border-border bg-background/95 backdrop-blur shrink-0">
              <div className="max-w-4xl mx-auto px-4 py-2">
                <div className="rounded-xl border border-border/60 bg-background shadow-sm">
                  <div className="relative">
                    <Textarea
                      ref={textareaRef}
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder="Ask a follow-up..."
                      rows={1}
                      className="resize-none pr-24 !min-h-[44px] max-h-32 rounded-xl border-0 bg-transparent shadow-none focus-visible:ring-0 text-sm py-2.5"
                    />
                    <div className="absolute right-2 bottom-1.5 flex items-center gap-1">
                      <Tooltip>
                        <TooltipTrigger
                          className="inline-flex items-center justify-center h-8 w-8 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors cursor-pointer"
                        >
                          <Mic className="h-4 w-4" />
                        </TooltipTrigger>
                        <TooltipContent>Use voice mode</TooltipContent>
                      </Tooltip>
                      <Button
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => handleSend()}
                        disabled={!input.trim() || isTyping}
                      >
                        <Send className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
