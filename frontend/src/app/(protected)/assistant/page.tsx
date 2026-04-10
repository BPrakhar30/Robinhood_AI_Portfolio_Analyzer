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

const PLACEHOLDER_REPLIES = [
  "I'm still being connected to the backend, but once I'm live I'll be able to analyze your full portfolio — holdings, allocation, performance, and more. Stay tuned!",
  "Great question! When the backend is ready, I'll pull your real positions and give you a data-driven answer. For now, think of this as a preview of what's coming.",
  "I appreciate the question! My portfolio analysis engine isn't wired up yet, but I'm designed to understand your holdings, spot concentration risks, compare benchmarks, and much more.",
];
let replyIndex = 0;

export default function AssistantPage() {
  const {
    activeSessionId,
    messages,
    createSession,
    addMessage,
  } = useChatStore();

  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const activeMessages = activeSessionId ? messages[activeSessionId] ?? [] : [];
  const isWelcome = activeMessages.length === 0;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeMessages.length, isTyping]);

  useEffect(() => {
    textareaRef.current?.focus();
  }, [activeSessionId, isWelcome]);

  const handleSend = (text?: string) => {
    const content = (text ?? input).trim();
    if (!content) return;

    let sessionId = activeSessionId;
    if (!sessionId) {
      sessionId = createSession();
    }

    const userMsg: ChatMessage = {
      id: generateId(),
      role: "user",
      content,
      timestamp: new Date().toISOString(),
    };
    addMessage(sessionId, userMsg);
    setInput("");

    setIsTyping(true);
    setTimeout(() => {
      const reply: ChatMessage = {
        id: generateId(),
        role: "assistant",
        content: PLACEHOLDER_REPLIES[replyIndex % PLACEHOLDER_REPLIES.length],
        timestamp: new Date().toISOString(),
      };
      replyIndex++;
      addMessage(sessionId!, reply);
      setIsTyping(false);
    }, 1200 + Math.random() * 800);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex absolute inset-0">
      {/* Chat sidebar — z-50 layers above topbar (z-40) */}
      {sidebarOpen && (
        <ChatSidebar onClose={() => setSidebarOpen(false)} />
      )}

      {/* Main chat area — z-30 stays below topbar (z-40), pt-14 offsets content */}
      <div className="flex-1 flex flex-col min-w-0 h-full pt-14 bg-background z-30">
        {/* Sidebar toggle when closed — aligned with main sidebar nav items */}
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
          /* ── Welcome state: centered ── */
          <div className="flex-1 flex flex-col items-center justify-center px-4">
            <div className="w-full max-w-2xl space-y-8">
              {/* Logo + headline */}
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

              {/* Input box */}
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

              {/* Prompt suggestions */}
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
          /* ── Active chat state ── */
          <>
            {/* Messages */}
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
                          ? "bg-primary text-primary-foreground rounded-br-md"
                          : "bg-muted rounded-bl-md"
                      )}
                    >
                      {msg.content}
                    </div>
                    {msg.role === "user" && (
                      <div className="h-8 w-8 rounded-lg bg-muted flex items-center justify-center shrink-0 mt-0.5">
                        <User className="h-4 w-4 text-muted-foreground" />
                      </div>
                    )}
                  </div>
                ))}

                {/* Typing indicator */}
                {isTyping && (
                  <div className="flex gap-3">
                    <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                      <Bot className="h-4 w-4 text-primary" />
                    </div>
                    <div className="bg-muted rounded-2xl rounded-bl-md px-4 py-3">
                      <div className="flex gap-1">
                        <span className="h-2 w-2 rounded-full bg-muted-foreground/40 animate-bounce [animation-delay:0ms]" />
                        <span className="h-2 w-2 rounded-full bg-muted-foreground/40 animate-bounce [animation-delay:150ms]" />
                        <span className="h-2 w-2 rounded-full bg-muted-foreground/40 animate-bounce [animation-delay:300ms]" />
                      </div>
                    </div>
                  </div>
                )}
                <div ref={bottomRef} />
              </div>
            </div>

            {/* Bottom input bar */}
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
