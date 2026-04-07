"use client";
import { cn } from "@/lib/utils";

interface TimestampTextProps {
  date: string | null;
  className?: string;
  fallback?: string;
}

function parseUTC(dateStr: string): Date {
  // Backend stores UTC but SQLite drops timezone info.
  // Append 'Z' so JS parses it as UTC instead of local time.
  if (!dateStr.endsWith("Z") && !dateStr.includes("+") && !/\d{2}:\d{2}$/.test(dateStr.slice(-6))) {
    return new Date(dateStr + "Z");
  }
  return new Date(dateStr);
}

export function formatTimestamp(dateStr: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(parseUTC(dateStr));
}

export function formatDateShort(dateStr: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(parseUTC(dateStr));
}

export function TimestampText({ date, className, fallback = "Never" }: TimestampTextProps) {
  if (!date) {
    return <span className={cn("text-muted-foreground", className)}>{fallback}</span>;
  }

  return (
    <span className={cn("tabular-nums text-muted-foreground", className)} suppressHydrationWarning>
      {formatTimestamp(date)}
    </span>
  );
}
