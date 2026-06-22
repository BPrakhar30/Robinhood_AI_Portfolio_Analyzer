"use client";

import Link from "next/link";
import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import { formatCurrency } from "@/components/portfolio/currency-text";
import type { AllocationBreakdown } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

// Amber palette matches the Incognito accent + assistant link color so the
// app reads as one product. amber-500 / 600 / 200 (Tailwind values in HSL).
const RING_COLOR = "hsl(38, 92%, 50%)";
const RING_ACTIVE = "hsl(38, 92%, 50%)";
const RING_DIM = "hsl(36, 82.50%, 75.30%)";

interface AllocationSectionProps {
  title: string;
  data: AllocationBreakdown[];
}

export function AllocationSection({ title, data }: AllocationSectionProps) {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  if (!data.length) {
    return (
      <section>
        <h2 className="text-lg font-semibold mb-4">{title}</h2>
        <p className="text-sm text-muted-foreground">No data available</p>
      </section>
    );
  }

  const handleToggle = (idx: number) =>
    setExpandedIndex((prev) => (prev === idx ? null : idx));

  const displayIndex = expandedIndex ?? hoveredIndex;
  const hasInteraction = hoveredIndex !== null || expandedIndex !== null;

  const getCellFill = (idx: number) => {
    if (expandedIndex === idx) return RING_ACTIVE;
    if (hasInteraction && hoveredIndex === idx) return RING_ACTIVE;
    if (hasInteraction) return RING_DIM;
    return RING_COLOR;
  };

  return (
    <section>
      <h2 className="text-lg font-semibold mb-6">{title}</h2>

      <div className="flex flex-col-reverse gap-6 lg:flex-row lg:gap-8">
        {/* Data list */}
        <div className="flex-1 min-w-0 space-y-0.5">
          {data.map((item, idx) => {
            const isExpanded = expandedIndex === idx;
            return (
              <div key={item.label}>
                {/* Row */}
                <button
                  type="button"
                  onClick={() => handleToggle(idx)}
                  onMouseEnter={() => setHoveredIndex(idx)}
                  onMouseLeave={() => setHoveredIndex(null)}
                  className={cn(
                    "flex w-full flex-col gap-2 rounded-lg px-3 py-2.5 text-left text-sm transition-colors cursor-pointer sm:flex-row sm:items-center sm:justify-between",
                    isExpanded
                      ? "bg-amber-50 dark:bg-amber-950/30"
                      : "hover:bg-muted/50"
                  )}
                >
                  <div className="flex min-w-0 items-center">
                    <span className={cn("truncate", isExpanded && "font-medium")}>
                      {item.label}
                    </span>
                  </div>
                  <div className="flex shrink-0 items-center justify-between gap-4 sm:ml-3 sm:justify-end">
                    <span className="text-muted-foreground tabular-nums">
                      {formatCurrency(item.value)}
                    </span>
                    <span className="w-16 text-right font-semibold tabular-nums">
                      {item.percent.toFixed(1)}%
                    </span>
                    <ChevronDown
                      className={cn(
                        "h-4 w-4 text-muted-foreground transition-transform duration-200",
                        isExpanded && "rotate-180"
                      )}
                    />
                  </div>
                </button>

                {/* Expandable holdings list */}
                {isExpanded && item.holdings?.length > 0 && (
                  <div className="mx-1 mt-1 mb-2 space-y-px overflow-hidden rounded-lg border bg-muted/30 sm:ml-9">
                    {item.holdings.map((h) => (
                      <div
                        key={h.symbol}
                        className="flex flex-col gap-2 px-3 py-2 text-xs hover:bg-muted/50 sm:flex-row sm:items-center sm:justify-between"
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <Link
                            href={`/markets/${encodeURIComponent(h.symbol)}`}
                            className="font-medium hover:text-amber-600 dark:hover:text-amber-400 transition-colors"
                          >
                            {h.symbol}
                          </Link>
                          <span className="truncate text-muted-foreground">
                            {h.name !== h.symbol ? h.name : ""}
                          </span>
                          <Badge
                            variant="outline"
                            className="text-[9px] capitalize px-1 py-0 leading-tight shrink-0"
                          >
                            {h.asset_type}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-3 shrink-0 ml-2">
                          <span className="text-muted-foreground tabular-nums">
                            {formatCurrency(h.market_value)}
                          </span>
                          <span className="w-12 text-right tabular-nums font-medium">
                            {h.percent.toFixed(1)}%
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Donut ring  -  sticky on desktop */}
        <div className="w-full shrink-0 self-start sm:max-w-xs sm:self-center lg:sticky lg:top-4 lg:w-64 lg:self-start">
          <div className="relative h-56 min-w-0 lg:h-64 [&_.recharts-sector]:outline-none [&_.recharts-pie]:outline-none">
            {/* ``minWidth`` / ``minHeight`` of 0 suppress Recharts' "-1 dims"
                preflight warning that otherwise fires on every chart during
                hydration and sticky-recalc in dev (StrictMode × 5 sections
                ≈ 10 warnings per page load). See
                https://github.com/recharts/recharts/issues/1423. */}
            <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
              <PieChart>
                <Pie
                  data={data}
                  cx="50%"
                  cy="50%"
                  innerRadius="68%"
                  outerRadius="90%"
                  paddingAngle={2}
                  dataKey="value"
                  nameKey="label"
                  strokeWidth={0}
                  onClick={(_, idx) => handleToggle(idx)}
                  onMouseEnter={(_, idx) => setHoveredIndex(idx)}
                  onMouseLeave={() => setHoveredIndex(null)}
                >
                  {data.map((_, idx) => (
                    <Cell
                      key={idx}
                      fill={getCellFill(idx)}
                      stroke={expandedIndex === idx ? "#fff" : "none"}
                      strokeWidth={expandedIndex === idx ? 2 : 0}
                      className="transition-[fill] duration-150 outline-none"
                      style={{ cursor: "pointer" }}
                    />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>

            {/* Center  -  category title by default, segment info on interaction */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              {displayIndex !== null && data[displayIndex] ? (
                <div className="text-center px-1">
                  <p className="text-2xl font-bold tabular-nums leading-tight">
                    {data[displayIndex].percent.toFixed(1)}%
                  </p>
                  <p className="text-[10px] text-muted-foreground mt-1 max-w-[7.5rem] mx-auto leading-snug break-words line-clamp-2">
                    {data[displayIndex].label}
                  </p>
                  <p className="text-[10px] text-muted-foreground/70 tabular-nums mt-0.5">
                    {formatCurrency(data[displayIndex].value)}
                  </p>
                </div>
              ) : (
                <p className="text-xs font-medium text-muted-foreground max-w-[7rem] text-center leading-snug">
                  {title}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
