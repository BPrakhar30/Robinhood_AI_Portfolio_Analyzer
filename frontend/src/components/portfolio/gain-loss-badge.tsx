import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface GainLossBadgeProps {
  value: number;
  format?: "currency" | "percent";
  className?: string;
}

export function GainLossBadge({ value, format = "currency", className }: GainLossBadgeProps) {
  const isPositive = value > 0;
  const isNegative = value < 0;
  const isZero = value === 0;

  const formatted =
    format === "percent"
      ? `${Math.abs(value).toFixed(2)}%`
      : new Intl.NumberFormat("en-US", {
          style: "currency",
          currency: "USD",
          minimumFractionDigits: 2,
        }).format(Math.abs(value));

  const Icon = isPositive ? TrendingUp : isNegative ? TrendingDown : Minus;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full tabular-nums",
        isPositive && "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
        isNegative && "bg-red-500/10 text-red-700 dark:text-red-400",
        isZero && "bg-zinc-500/10 text-zinc-600 dark:text-zinc-400",
        className
      )}
    >
      <Icon className="h-3 w-3" />
      {isPositive && "+"}
      {isNegative && "−"}
      {formatted}
    </span>
  );
}
