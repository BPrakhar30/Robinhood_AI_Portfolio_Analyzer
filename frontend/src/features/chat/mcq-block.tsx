"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { HelpCircle, CheckCircle2 } from "lucide-react";

interface McqOption {
  label: string;
  description: string;
}

interface McqBlockProps {
  question: string;
  options: McqOption[];
  onSelect?: (fullMessage: string) => void;
  disabled?: boolean;
}

const MCQ_REGEX = /---mcq---\s*\n([\s\S]*?)\n---end-mcq---/g;
const OPTION_LINE = /^-\s+(.+?):\s+(.+)$/;
const QUESTION_LINE = /^\*\*(.+?)\*\*$/;

export function parseMcqBlocks(content: string): {
  segments: Array<{ type: "text"; content: string } | { type: "mcq"; question: string; options: McqOption[] }>;
  hasMcq: boolean;
} {
  const segments: Array<
    { type: "text"; content: string } | { type: "mcq"; question: string; options: McqOption[] }
  > = [];
  let lastIndex = 0;

  for (const match of content.matchAll(MCQ_REGEX)) {
    const before = content.slice(lastIndex, match.index);
    if (before.trim()) {
      segments.push({ type: "text", content: before });
    }

    const inner = match[1].trim();
    const lines = inner.split("\n").map((l) => l.trim()).filter(Boolean);

    let question = "";
    const options: McqOption[] = [];

    for (const line of lines) {
      const qMatch = line.match(QUESTION_LINE);
      if (qMatch) {
        question = qMatch[1];
        continue;
      }
      const oMatch = line.match(OPTION_LINE);
      if (oMatch) {
        options.push({ label: oMatch[1], description: oMatch[2] });
      }
    }

    if (question && options.length >= 2) {
      segments.push({ type: "mcq", question, options });
    } else {
      segments.push({ type: "text", content: match[0] });
    }

    lastIndex = (match.index ?? 0) + match[0].length;
  }

  const remaining = content.slice(lastIndex);
  if (remaining.trim()) {
    segments.push({ type: "text", content: remaining });
  }

  return { segments, hasMcq: segments.some((s) => s.type === "mcq") };
}

export function McqBlock({ question, options, onSelect, disabled }: McqBlockProps) {
  const [selected, setSelected] = useState<string | null>(null);

  const handleSelect = (opt: McqOption) => {
    if (disabled || selected) return;
    setSelected(opt.label);
    onSelect?.(`${opt.label}: ${opt.description}`);
  };

  return (
    <div className="my-3 rounded-xl border border-amber-500/30 bg-amber-500/5 p-3 space-y-2.5">
      <div className="flex items-start gap-2">
        <HelpCircle className="h-4 w-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
        <p className="text-sm font-medium leading-snug">{question}</p>
      </div>
      <div className="grid gap-1.5 pl-6">
        {options.map((opt) => {
          const isSelected = selected === opt.label;
          return (
            <button
              key={opt.label}
              type="button"
              onClick={() => handleSelect(opt)}
              disabled={disabled || (!!selected && !isSelected)}
              className={cn(
                "flex items-start gap-2.5 rounded-lg border px-3 py-2 text-left text-xs leading-relaxed transition-all",
                isSelected
                  ? "border-amber-500 bg-amber-500/10 text-foreground"
                  : selected
                    ? "border-border/40 bg-muted/20 text-muted-foreground/50 cursor-default"
                    : "border-border/70 bg-background hover:border-amber-500/50 hover:bg-amber-500/5 cursor-pointer",
              )}
            >
              {isSelected ? (
                <CheckCircle2 className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
              ) : (
                <div className="h-3.5 w-3.5 rounded-full border border-border/80 shrink-0 mt-0.5" />
              )}
              <div>
                <span className="font-medium">{opt.label}</span>
                <span className="text-muted-foreground"> - {opt.description}</span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
