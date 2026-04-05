import { cn } from "@/lib/utils";

interface TimestampTextProps {
  date: string | null;
  className?: string;
  fallback?: string;
}

export function formatTimestamp(dateStr: string): string {
  const date = new Date(dateStr);
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

export function formatDateShort(dateStr: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(dateStr));
}

export function TimestampText({ date, className, fallback = "Never" }: TimestampTextProps) {
  if (!date) {
    return <span className={cn("text-muted-foreground", className)}>{fallback}</span>;
  }

  return (
    <span className={cn("tabular-nums text-muted-foreground", className)}>
      {formatTimestamp(date)}
    </span>
  );
}
