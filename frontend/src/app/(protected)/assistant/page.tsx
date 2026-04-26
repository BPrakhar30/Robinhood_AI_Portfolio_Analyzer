"use client";

import {
  useRef,
  useEffect,
  useState,
  useCallback,
  type KeyboardEvent,
} from "react";
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
  Ghost,
  X,
  Copy,
  Check,
  Pencil,
  RotateCcw,
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
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";

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
    setActiveSession,
    addMessage,
    appendToMessage,
    truncateMessages,
  } = useChatStore();

  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  // Temporary (ephemeral) chat: messages live only in this component and are
  // streamed WITHOUT a session_id so the backend doesn't persist them either.
  const [temporaryMode, setTemporaryMode] = useState(false);
  const [tempMessages, setTempMessages] = useState<ChatMessage[]>([]);

  // Inline message editor — only one message is editable at a time.
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState("");

  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  // Track the in-flight stream so a new question / unmount cancels it.
  const abortRef = useRef<AbortController | null>(null);

  const persistedMessages = activeSessionId ? messages[activeSessionId] ?? [] : [];
  const activeMessages = temporaryMode ? tempMessages : persistedMessages;
  const isWelcome = activeMessages.length === 0;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeMessages.length, isTyping]);

  useEffect(() => {
    textareaRef.current?.focus();
  }, [activeSessionId, isWelcome, temporaryMode]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  // Entering temp mode clears the visible persisted chat; exiting wipes the
  // ephemeral transcript so nothing leaks between contexts.
  const enterTemporaryMode = useCallback(() => {
    abortRef.current?.abort();
    setActiveSession(null);
    setTempMessages([]);
    setTemporaryMode(true);
    setEditingMessageId(null);
    setInput("");
  }, [setActiveSession]);

  const exitTemporaryMode = useCallback(() => {
    abortRef.current?.abort();
    setTemporaryMode(false);
    setTempMessages([]);
    setEditingMessageId(null);
    setInput("");
  }, []);

  // Selecting an existing session or spawning a fresh one from the sidebar
  // must also take us out of temporary mode.
  useEffect(() => {
    if (temporaryMode && activeSessionId) {
      setTemporaryMode(false);
      setTempMessages([]);
      setEditingMessageId(null);
    }
  }, [activeSessionId, temporaryMode]);

  // "New chat" is intentionally deferred: it only clears the current
  // selection so the welcome screen shows. The session row is created on
  // the very first user message — this keeps empty placeholder sessions
  // out of the sidebar.
  const handleNewChat = useCallback(() => {
    abortRef.current?.abort();
    setTemporaryMode(false);
    setTempMessages([]);
    setEditingMessageId(null);
    setActiveSession(null);
    setInput("");
    setIsTyping(false);
  }, [setActiveSession]);

  const addTempMessage = useCallback((msg: ChatMessage) => {
    setTempMessages((prev) => [...prev, msg]);
  }, []);

  const appendToTempMessage = useCallback((id: string, delta: string) => {
    setTempMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, content: m.content + delta } : m)),
    );
  }, []);

  /**
   * Low-level sender. Given an *already-prepared* conversation tail, push
   * a user turn + assistant placeholder, then stream into them.
   *
   * ``prepareSessionId`` lets the caller decide whether to reuse an
   * existing session, create a new one, or stay ephemeral.
   */
  const sendTurn = useCallback(
    async (content: string, ephemeral: boolean, sid: string | null) => {
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

      if (ephemeral) {
        addTempMessage(userMsg);
        addTempMessage(assistantMsg);
      } else if (sid) {
        addMessage(sid, userMsg);
        addMessage(sid, assistantMsg);
      }

      setInput("");
      setIsTyping(true);

      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      await streamAssistant(
        content,
        {
          onDelta: (delta) => {
            if (ephemeral) appendToTempMessage(assistantId, delta);
            else if (sid) appendToMessage(sid, assistantId, delta);
          },
          onDone: () => {
            setIsTyping(false);
            abortRef.current = null;
          },
          onError: (message) => {
            const note = `\n\n_${message}_`;
            if (ephemeral) appendToTempMessage(assistantId, note);
            else if (sid) appendToMessage(sid, assistantId, note);
            setIsTyping(false);
            abortRef.current = null;
          },
        },
        {
          sessionId: ephemeral ? undefined : sid ?? undefined,
          signal: controller.signal,
        },
      );
    },
    [addMessage, addTempMessage, appendToMessage, appendToTempMessage],
  );

  const handleSend = async (text?: string) => {
    const content = (text ?? input).trim();
    if (!content || isTyping) return;

    if (temporaryMode) {
      await sendTurn(content, true, null);
      return;
    }

    // Deferred creation: the session row is materialized on the first
    // submit, never on "+ New chat".
    let sid = activeSessionId;
    if (!sid) {
      sid = await createSession();
      if (!sid) return;
    }
    await sendTurn(content, false, sid);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  /* ── Edit & regenerate ───────────────────────────────────────── */

  const startEdit = useCallback((msg: ChatMessage) => {
    setEditingMessageId(msg.id);
    setEditDraft(msg.content);
  }, []);

  const cancelEdit = useCallback(() => {
    setEditingMessageId(null);
    setEditDraft("");
  }, []);

  const submitEdit = useCallback(
    async (userIndex: number) => {
      const newContent = editDraft.trim();
      if (!newContent || isTyping) return;

      setEditingMessageId(null);
      setEditDraft("");

      if (temporaryMode) {
        // Replace the ephemeral tail; skip the network dance.
        setTempMessages((prev) => prev.slice(0, userIndex));
        await sendTurn(newContent, true, null);
        return;
      }

      if (!activeSessionId) return;
      // Drop the edited user message + everything after it from both the
      // local store and the database, then append a fresh turn. Abort on
      // truncate failure so we don't stack a duplicate turn.
      try {
        await truncateMessages(activeSessionId, userIndex);
      } catch {
        return;
      }
      await sendTurn(newContent, false, activeSessionId);
    },
    [
      activeSessionId,
      editDraft,
      isTyping,
      sendTurn,
      temporaryMode,
      truncateMessages,
    ],
  );

  const regenerateFromAssistant = useCallback(
    async (assistantIndex: number) => {
      if (isTyping) return;
      const prevUser = activeMessages[assistantIndex - 1];
      if (!prevUser || prevUser.role !== "user") return;

      const prompt = prevUser.content;

      if (temporaryMode) {
        setTempMessages((prev) => prev.slice(0, assistantIndex - 1));
        await sendTurn(prompt, true, null);
        return;
      }

      if (!activeSessionId) return;
      try {
        await truncateMessages(activeSessionId, assistantIndex - 1);
      } catch {
        return;
      }
      await sendTurn(prompt, false, activeSessionId);
    },
    [
      activeMessages,
      activeSessionId,
      isTyping,
      sendTurn,
      temporaryMode,
      truncateMessages,
    ],
  );

  /* ── Render ─────────────────────────────────────────────────── */

  return (
    // Anchor at top-14 so the pane sits flush below the topbar (the red line
    // in the mock). inset-0 + top-14 collapses left/right/bottom to 0.
    <div className="flex absolute inset-0 top-14">
      {sidebarOpen && (
        <ChatSidebar
          onClose={() => setSidebarOpen(false)}
          onNewChat={handleNewChat}
        />
      )}

      <div className="flex-1 flex flex-col min-w-0 h-full bg-background z-30 relative">
        {/* Floating controls when the sidebar is collapsed: + at top, open
            button pinned to the bottom so it occupies the same spot that
            Hide sidebar lives in when the panel is expanded. */}
        {!sidebarOpen && (
          <>
            <Tooltip>
              <TooltipTrigger
                className="absolute top-2 left-2 z-10 inline-flex items-center justify-center h-9 w-9 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors cursor-pointer"
                onClick={handleNewChat}
              >
                <Plus className="h-4 w-4" />
              </TooltipTrigger>
              <TooltipContent side="right">New chat</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger
                className="absolute bottom-3 left-2 z-10 inline-flex items-center justify-center h-9 w-9 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors cursor-pointer"
                onClick={() => setSidebarOpen(true)}
              >
                <PanelLeftOpen className="h-4 w-4" />
              </TooltipTrigger>
              <TooltipContent side="right">Show sidebar</TooltipContent>
            </Tooltip>
          </>
        )}

        <Sheet open={mobileSidebarOpen} onOpenChange={setMobileSidebarOpen}>
          <SheetTrigger className="absolute top-2 left-2 z-10 inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground lg:hidden">
            <PanelLeftOpen className="h-4 w-4" />
          </SheetTrigger>
          <SheetContent side="left" className="p-0 w-[86vw] max-w-sm lg:hidden">
            <ChatSidebar
              variant="mobile"
              onClose={() => setMobileSidebarOpen(false)}
              onNewChat={() => {
                handleNewChat();
                setMobileSidebarOpen(false);
              }}
            />
          </SheetContent>
        </Sheet>

        {/* Incognito toggle: label on welcome, icon-only inside a chat.
            Tooltip copy stays "Incognito mode" in every state. */}
        <div className="absolute top-2 right-3 z-10 flex items-center gap-2">
          <IncognitoToggle
            active={temporaryMode}
            showLabel={isWelcome}
            onEnter={enterTemporaryMode}
            onExit={exitTemporaryMode}
          />
        </div>

        {isWelcome ? (
          <div className="flex-1 flex flex-col items-center justify-center px-4">
            <div className="w-full max-w-2xl xl:max-w-3xl 2xl:max-w-4xl space-y-8">
              <div className="text-center space-y-3">
                <div
                  className={cn(
                    "h-14 w-14 rounded-2xl flex items-center justify-center mx-auto",
                    temporaryMode
                      ? "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                      : "bg-primary/10 text-primary",
                  )}
                >
                  {temporaryMode ? (
                    <Ghost className="h-7 w-7" />
                  ) : (
                    <Sparkles className="h-7 w-7" />
                  )}
                </div>
                <h1 className="text-2xl font-semibold tracking-tight">
                  {temporaryMode
                    ? "Incognito mode"
                    : "What would you like to know?"}
                </h1>
                <p className="text-sm text-muted-foreground max-w-sm mx-auto">
                  {temporaryMode
                    ? "This conversation won't be saved to your history."
                    : "I have full context of your portfolio — ask away."}
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
                      <TooltipTrigger className="inline-flex items-center justify-center h-8 w-8 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors cursor-pointer">
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
              <div className="max-w-3xl xl:max-w-4xl 2xl:max-w-5xl mx-auto px-3 py-5 space-y-6 sm:px-4 sm:py-6">
                {activeMessages.map((msg, index) => (
                  <MessageItem
                    key={msg.id}
                    msg={msg}
                    index={index}
                    temporaryMode={temporaryMode}
                    isEditing={editingMessageId === msg.id}
                    editDraft={editDraft}
                    onEditDraftChange={setEditDraft}
                    onStartEdit={() => startEdit(msg)}
                    onCancelEdit={cancelEdit}
                    onSubmitEdit={() => submitEdit(index)}
                    onRegenerate={() => regenerateFromAssistant(index)}
                    canRegenerate={!isTyping && index > 0}
                    canEdit={!isTyping}
                  />
                ))}

                <div ref={bottomRef} />
              </div>
            </div>

            <div className="border-t border-border bg-background/95 backdrop-blur shrink-0">
              <div className="max-w-3xl xl:max-w-4xl 2xl:max-w-5xl mx-auto px-3 py-2 sm:px-4">
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
                        <TooltipTrigger className="inline-flex items-center justify-center h-8 w-8 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors cursor-pointer">
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

/* ── Incognito toggle pill ──────────────────────────────────────── */

function IncognitoToggle({
  active,
  showLabel,
  onEnter,
  onExit,
}: {
  active: boolean;
  showLabel: boolean;
  onEnter: () => void;
  onExit: () => void;
}) {
  const activeClass = cn(
    "inline-flex items-center gap-1.5 rounded-full border border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400 cursor-pointer hover:bg-amber-500/15 transition-colors",
    showLabel ? "px-2.5 py-1 text-xs font-medium" : "h-8 w-8 justify-center",
  );
  const idleClass = cn(
    "inline-flex items-center gap-1.5 rounded-full border border-border/70 bg-background hover:bg-accent text-muted-foreground hover:text-foreground transition-colors cursor-pointer",
    showLabel ? "px-2.5 py-1 text-xs font-medium" : "h-8 w-8 justify-center",
  );

  const inner = active ? (
    <>
      <Ghost className="h-3.5 w-3.5" />
      {showLabel && (
        <>
          <span>Incognito mode</span>
          <X className="h-3 w-3 ml-0.5" />
        </>
      )}
    </>
  ) : (
    <>
      <Ghost className="h-3.5 w-3.5" />
      {showLabel && <span>Incognito mode</span>}
    </>
  );

  // Chat mode (no label) shows the icon alone — no tooltip, by request.
  // Welcome mode keeps the tooltip so first-time users get the affordance.
  if (!showLabel) {
    return (
      <button
        type="button"
        onClick={active ? onExit : onEnter}
        className={active ? activeClass : idleClass}
      >
        {inner}
      </button>
    );
  }

  return (
    <Tooltip>
      <TooltipTrigger
        onClick={active ? onExit : onEnter}
        className={active ? activeClass : idleClass}
      >
        {inner}
      </TooltipTrigger>
      <TooltipContent side="bottom">Incognito mode</TooltipContent>
    </Tooltip>
  );
}

/* ── Per-message view + actions ─────────────────────────────────── */

interface MessageItemProps {
  msg: ChatMessage;
  index: number;
  temporaryMode: boolean;
  isEditing: boolean;
  editDraft: string;
  onEditDraftChange: (v: string) => void;
  onStartEdit: () => void;
  onCancelEdit: () => void;
  onSubmitEdit: () => void;
  onRegenerate: () => void;
  canRegenerate: boolean;
  canEdit: boolean;
}

function MessageItem({
  msg,
  temporaryMode,
  isEditing,
  editDraft,
  onEditDraftChange,
  onStartEdit,
  onCancelEdit,
  onSubmitEdit,
  onRegenerate,
  canRegenerate,
  canEdit,
}: MessageItemProps) {
  const isUser = msg.role === "user";
  const isAssistant = msg.role === "assistant";
  const hasContent = !!msg.content?.length;

  return (
    <div className={cn("flex flex-col gap-1 group/msg", isUser ? "items-end" : "items-start")}>
      <div
        className={cn(
          "flex gap-3 w-full",
          isUser ? "justify-end" : "justify-start",
        )}
      >
        {isAssistant && (
          <div
            className={cn(
              "h-8 w-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5",
              temporaryMode
                ? "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                : "bg-primary/10 text-primary",
            )}
          >
            {temporaryMode ? <Ghost className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
          </div>
        )}

        {isEditing && isUser ? (
          <div className="w-full max-w-[calc(100%-3rem)] rounded-2xl bg-muted/60 border border-border p-2 space-y-2 sm:max-w-[80%]">
            <Textarea
              value={editDraft}
              onChange={(e) => onEditDraftChange(e.target.value)}
              rows={3}
              className="resize-none min-h-[72px] text-sm bg-background"
              autoFocus
            />
            <div className="flex items-center justify-end gap-2">
              <Button variant="ghost" size="sm" className="h-7 cursor-pointer" onClick={onCancelEdit}>
                Cancel
              </Button>
              <Button
                size="sm"
                className="h-7 cursor-pointer"
                onClick={onSubmitEdit}
                disabled={!editDraft.trim()}
              >
                Send
              </Button>
            </div>
          </div>
        ) : (
          <div
            className={cn(
              "rounded-2xl px-4 py-3 text-sm leading-relaxed max-w-[calc(100%-3rem)] sm:max-w-[80%]",
              isUser
                ? "bg-primary text-primary-foreground rounded-br-md whitespace-pre-wrap"
                : "bg-muted rounded-bl-md",
            )}
          >
            {isAssistant ? (
              hasContent ? (
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
        )}

        {isUser && !isEditing && (
          <div className="h-8 w-8 rounded-lg bg-muted flex items-center justify-center shrink-0 mt-0.5">
            <User className="h-4 w-4 text-muted-foreground" />
          </div>
        )}
      </div>

      {/* Per-message actions. Edit / Copy for user turns (bottom-right),
          Copy / Regenerate for assistant turns (bottom-left). Hidden while
          the inline editor for this bubble is active. */}
      {!isEditing && hasContent && (
        <MessageActions
          align={isUser ? "right" : "left"}
          content={msg.content}
          onEdit={isUser && canEdit ? onStartEdit : undefined}
          onRegenerate={isAssistant && canRegenerate ? onRegenerate : undefined}
        />
      )}
    </div>
  );
}

/* ── Action row (copy + edit or copy + regenerate) ─────────────── */

function MessageActions({
  align,
  content,
  onEdit,
  onRegenerate,
}: {
  align: "left" | "right";
  content: string;
  onEdit?: () => void;
  onRegenerate?: () => void;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard blocked — silently ignore. */
    }
  };

  // Indent the action row past the avatar so it visually lines up with the
  // bubble edge rather than the avatar.
  const sidePadding = align === "left" ? "pl-11" : "pr-11";

  return (
    <div
      className={cn(
        "flex items-center gap-1 text-muted-foreground opacity-100 transition-opacity md:opacity-0 md:group-hover/msg:opacity-100 md:focus-within:opacity-100",
        align === "left" ? "self-start" : "self-end",
        sidePadding,
      )}
    >
      <Tooltip>
        <TooltipTrigger
          onClick={handleCopy}
          className="inline-flex items-center justify-center h-7 w-7 rounded-md hover:bg-accent hover:text-foreground transition-colors cursor-pointer"
        >
          {copied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
        </TooltipTrigger>
        <TooltipContent side="bottom">{copied ? "Copied" : "Copy"}</TooltipContent>
      </Tooltip>

      {onEdit && (
        <Tooltip>
          <TooltipTrigger
            onClick={onEdit}
            className="inline-flex items-center justify-center h-7 w-7 rounded-md hover:bg-accent hover:text-foreground transition-colors cursor-pointer"
          >
            <Pencil className="h-3.5 w-3.5" />
          </TooltipTrigger>
          <TooltipContent side="bottom">Edit message</TooltipContent>
        </Tooltip>
      )}

      {onRegenerate && (
        <Tooltip>
          <TooltipTrigger
            onClick={onRegenerate}
            className="inline-flex items-center justify-center h-7 w-7 rounded-md hover:bg-accent hover:text-foreground transition-colors cursor-pointer"
          >
            <RotateCcw className="h-3.5 w-3.5" />
          </TooltipTrigger>
          <TooltipContent side="bottom">Regenerate response</TooltipContent>
        </Tooltip>
      )}
    </div>
  );
}
