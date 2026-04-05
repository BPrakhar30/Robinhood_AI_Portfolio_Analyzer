import { cn } from "@/lib/utils";

interface CurrencyTextProps {
  value: number;
  currency?: string;
  className?: string;
  showSign?: boolean;
}

export function formatCurrency(value: number, currency = "USD"): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function CurrencyText({ value, currency = "USD", className, showSign }: CurrencyTextProps) {
  const formatted = formatCurrency(Math.abs(value), currency);
  const prefix = showSign && value !== 0 ? (value > 0 ? "+" : "−") : value < 0 ? "−" : "";

  return (
    <span
      className={cn(
        "tabular-nums font-medium",
        showSign && value > 0 && "text-emerald-600 dark:text-emerald-400",
        showSign && value < 0 && "text-red-600 dark:text-red-400",
        className
      )}
    >
      {prefix}
      {value < 0 && !showSign ? `(${formatted})` : formatted}
    </span>
  );
}
