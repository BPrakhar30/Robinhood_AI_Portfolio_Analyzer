"use client";

import { cn } from "@/lib/utils";
import { GainLossBadge } from "@/components/portfolio/gain-loss-badge";

interface GainLossDisplayProps {
  value: number;
  invested: number;
  align?: "left" | "right";
  className?: string;
}

export function getGainLossPercent(value: number, invested: number): number {
  if (!Number.isFinite(value) || !Number.isFinite(invested) || invested <= 0) {
    return 0;
  }

  return (value / invested) * 100;
}

export function GainLossDisplay({
  value,
  invested,
  align = "left",
  className,
}: GainLossDisplayProps) {
  const percent = getGainLossPercent(value, invested);
  const isPositive = percent > 0;
  const isNegative = percent < 0;
  const sign = isPositive ? "+" : isNegative ? "-" : "";

  return (
    <div
      className={cn(
        "flex flex-col gap-1",
        align === "right" ? "items-end text-right" : "items-start text-left",
        className
      )}
    >
      <GainLossBadge value={value} />
      <span
        className={cn(
          "text-xs tabular-nums",
          isPositive && "text-emerald-700 dark:text-emerald-400",
          isNegative && "text-red-700 dark:text-red-400",
          !isPositive && !isNegative && "text-muted-foreground"
        )}
      >
        {sign}
        {Math.abs(percent).toFixed(2)}%
      </span>
    </div>
  );
}
