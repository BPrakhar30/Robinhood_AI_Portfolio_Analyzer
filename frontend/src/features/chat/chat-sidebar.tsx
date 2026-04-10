"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import {
  Plus,
  Search,
  MessageSquare,
  Trash2,
  MoreHorizontal,
  Pencil,
  Star,
  Archive,
  ArchiveRestore,
  PanelLeftClose,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useChatStore } from "./store";
import { cn } from "@/lib/utils";

const MIN_WIDTH = 200;
const MAX_WIDTH = 360;
const DEFAULT_WIDTH = 240;

interface ChatSidebarProps {
  onClose?: () => void;
}

export function ChatSidebar({ onClose }: ChatSidebarProps) {
  const {
    sessions,
    activeSessionId,
    createSession,
    setActiveSession,
    deleteSession,
    renameSession,
    toggleStar,
    toggleArchive,
  } = useChatStore();

  const [search, setSearch] = useState("");
  const [showArchived, setShowArchived] = useState(false);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const renameInputRef = useRef<HTMLInputElement>(null);

  /* ── Drag-to-resize ── */
  const [width, setWidth] = useState(DEFAULT_WIDTH);
  const isDragging = useRef(false);
  const sidebarRef = useRef<HTMLElement>(null);

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isDragging.current = true;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, []);

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!isDragging.current || !sidebarRef.current) return;
      const rect = sidebarRef.current.getBoundingClientRect();
      const newWidth = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, e.clientX - rect.left));
      setWidth(newWidth);
    };
    const onMouseUp = () => {
      isDragging.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, []);

  /* ── Rename helpers ── */
  const startRename = (id: string, currentTitle: string) => {
    setRenamingId(id);
    setRenameValue(currentTitle);
    setTimeout(() => renameInputRef.current?.focus(), 0);
  };

  const commitRename = () => {
    if (renamingId && renameValue.trim()) {
      renameSession(renamingId, renameValue.trim());
    }
    setRenamingId(null);
  };

  /* ── Filtered lists ── */
  const visible = sessions.filter((s) => s.archived === showArchived);
  const filtered = search
    ? visible.filter(
        (s) =>
          s.title.toLowerCase().includes(search.toLowerCase()) ||
          s.preview.toLowerCase().includes(search.toLowerCase())
      )
    : visible;

  const starred = filtered.filter((s) => s.starred);
  const unstarred = filtered.filter((s) => !s.starred);

  return (
    <aside
      ref={sidebarRef}
      style={{ width }}
      className="relative border-r border-border bg-background flex flex-col h-full shrink-0 hidden lg:flex z-50"
    >
      {/* Header */}
      <div className="p-3 border-b border-border space-y-2 shrink-0">
        <Button
          className="w-full justify-start gap-2 h-8"
          size="sm"
          onClick={() => {
            setShowArchived(false);
            createSession();
          }}
        >
          <Plus className="h-4 w-4" />
          New chat
        </Button>

        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            placeholder="Search chats..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8 h-8 text-xs"
          />
        </div>
      </div>

      {/* Archive toggle */}
      <div className="flex border-b border-border shrink-0">
        <button
          type="button"
          onClick={() => setShowArchived(false)}
          className={cn(
            "flex-1 py-1.5 text-[11px] font-medium transition-colors cursor-pointer",
            !showArchived
              ? "text-foreground border-b-2 border-primary"
              : "text-muted-foreground hover:text-foreground"
          )}
        >
          Chats
        </button>
        <button
          type="button"
          onClick={() => setShowArchived(true)}
          className={cn(
            "flex-1 py-1.5 text-[11px] font-medium transition-colors cursor-pointer",
            showArchived
              ? "text-foreground border-b-2 border-primary"
              : "text-muted-foreground hover:text-foreground"
          )}
        >
          Archived
        </button>
      </div>

      {/* Chat list */}
      <div className="flex-1 overflow-y-auto py-1">
        {filtered.length === 0 ? (
          <div className="px-4 py-8 text-center">
            {showArchived ? (
              <>
                <Archive className="h-8 w-8 text-muted-foreground/40 mx-auto mb-2" />
                <p className="text-xs text-muted-foreground">
                  {search ? "No archived chats match your search" : "No archived chats"}
                </p>
                <p className="text-[11px] text-muted-foreground/60 mt-1">
                  Archive chats you want to keep but hide from your main list
                </p>
              </>
            ) : (
              <>
                <MessageSquare className="h-8 w-8 text-muted-foreground/40 mx-auto mb-2" />
                <p className="text-xs text-muted-foreground">
                  {search ? "No chats match your search" : "No conversations yet"}
                </p>
              </>
            )}
          </div>
        ) : (
          <>
            {/* Starred section */}
            {starred.length > 0 && !showArchived && (
              <>
                <p className="px-3 pt-2 pb-1 text-[10px] font-semibold text-muted-foreground uppercase tracking-widest">
                  Starred
                </p>
                {starred.map((session) => (
                  <ChatRow
                    key={session.id}
                    session={session}
                    isActive={session.id === activeSessionId}
                    isRenaming={session.id === renamingId}
                    renameValue={renameValue}
                    renameInputRef={renameInputRef}
                    showArchived={showArchived}
                    onSelect={() => setActiveSession(session.id)}
                    onStartRename={() => startRename(session.id, session.title)}
                    onRenameChange={setRenameValue}
                    onCommitRename={commitRename}
                    onToggleStar={() => toggleStar(session.id)}
                    onToggleArchive={() => toggleArchive(session.id)}
                    onDelete={() => deleteSession(session.id)}
                  />
                ))}
              </>
            )}

            {/* Regular / unstarred section */}
            {unstarred.length > 0 && (
              <>
                {starred.length > 0 && !showArchived && (
                  <p className="px-3 pt-3 pb-1 text-[10px] font-semibold text-muted-foreground uppercase tracking-widest">
                    Recent
                  </p>
                )}
                {unstarred.map((session) => (
                  <ChatRow
                    key={session.id}
                    session={session}
                    isActive={session.id === activeSessionId}
                    isRenaming={session.id === renamingId}
                    renameValue={renameValue}
                    renameInputRef={renameInputRef}
                    showArchived={showArchived}
                    onSelect={() => setActiveSession(session.id)}
                    onStartRename={() => startRename(session.id, session.title)}
                    onRenameChange={setRenameValue}
                    onCommitRename={commitRename}
                    onToggleStar={() => toggleStar(session.id)}
                    onToggleArchive={() => toggleArchive(session.id)}
                    onDelete={() => deleteSession(session.id)}
                  />
                ))}
              </>
            )}
          </>
        )}
      </div>

      {/* Close button */}
      {onClose && (
        <div className="border-t border-border p-2 shrink-0">
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-center gap-2 text-muted-foreground hover:text-foreground cursor-pointer"
            onClick={onClose}
          >
            <PanelLeftClose className="h-4 w-4" />
            Hide sidebar
          </Button>
        </div>
      )}

      {/* Drag handle */}
      <div
        onMouseDown={onMouseDown}
        className="absolute top-0 right-0 w-1 h-full cursor-col-resize hover:bg-primary/20 active:bg-primary/30 transition-colors z-10"
      />
    </aside>
  );
}

/* ── Single chat row ── */

interface ChatRowProps {
  session: import("./types").ChatSession;
  isActive: boolean;
  isRenaming: boolean;
  renameValue: string;
  renameInputRef: React.RefObject<HTMLInputElement | null>;
  showArchived: boolean;
  onSelect: () => void;
  onStartRename: () => void;
  onRenameChange: (v: string) => void;
  onCommitRename: () => void;
  onToggleStar: () => void;
  onToggleArchive: () => void;
  onDelete: () => void;
}

function ChatRow({
  session,
  isActive,
  isRenaming,
  renameValue,
  renameInputRef,
  showArchived,
  onSelect,
  onStartRename,
  onRenameChange,
  onCommitRename,
  onToggleStar,
  onToggleArchive,
  onDelete,
}: ChatRowProps) {
  return (
    <div
      className={cn(
        "group flex items-start gap-2 px-3 py-2 mx-1 rounded-md cursor-pointer transition-colors",
        isActive
          ? "bg-accent text-accent-foreground"
          : "hover:bg-accent/50 text-muted-foreground hover:text-foreground"
      )}
      onClick={onSelect}
    >
      <div className="relative mt-0.5 shrink-0">
        <MessageSquare className="h-4 w-4" />
        {session.starred && (
          <Star className="h-2 w-2 text-amber-500 fill-amber-500 absolute -top-1 -right-1" />
        )}
      </div>

      <div className="flex-1 min-w-0">
        {isRenaming ? (
          <input
            ref={renameInputRef}
            value={renameValue}
            onChange={(e) => onRenameChange(e.target.value)}
            onBlur={onCommitRename}
            onKeyDown={(e) => {
              if (e.key === "Enter") onCommitRename();
              if (e.key === "Escape") onCommitRename();
            }}
            onClick={(e) => e.stopPropagation()}
            className="w-full text-sm font-medium bg-background border border-border rounded px-1.5 py-0.5 outline-none focus:ring-1 focus:ring-primary/40"
          />
        ) : (
          <p className="text-sm font-medium truncate">{session.title}</p>
        )}
        <p className="text-[11px] text-muted-foreground truncate mt-0.5">
          {session.preview || "Empty conversation"}
        </p>
      </div>

      {/* Context menu */}
      <DropdownMenu>
        <DropdownMenuTrigger
          onClick={(e) => e.stopPropagation()}
          className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-accent transition-opacity shrink-0 cursor-pointer"
        >
          <MoreHorizontal className="h-3.5 w-3.5" />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-40">
          <DropdownMenuItem
            className="cursor-pointer"
            onClick={(e) => {
              e.stopPropagation();
              onStartRename();
            }}
          >
            <Pencil className="h-3.5 w-3.5 mr-2" />
            Rename
          </DropdownMenuItem>
          <DropdownMenuItem
            className="cursor-pointer"
            onClick={(e) => {
              e.stopPropagation();
              onToggleStar();
            }}
          >
            <Star
              className={cn(
                "h-3.5 w-3.5 mr-2",
                session.starred && "fill-amber-500 text-amber-500"
              )}
            />
            {session.starred ? "Unstar" : "Star"}
          </DropdownMenuItem>
          <DropdownMenuItem
            className="cursor-pointer"
            onClick={(e) => {
              e.stopPropagation();
              onToggleArchive();
            }}
          >
            {showArchived ? (
              <>
                <ArchiveRestore className="h-3.5 w-3.5 mr-2" />
                Unarchive
              </>
            ) : (
              <>
                <Archive className="h-3.5 w-3.5 mr-2" />
                Archive
              </>
            )}
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            className="text-destructive focus:text-destructive cursor-pointer"
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
          >
            <Trash2 className="h-3.5 w-3.5 mr-2" />
            Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
