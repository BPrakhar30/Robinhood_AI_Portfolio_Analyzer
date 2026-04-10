"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import { formatCurrency } from "@/components/portfolio/currency-text";
import type { AllocationBreakdown } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

const RING_COLOR = "hsl(239, 70%, 62%)";
const RING_ACTIVE = "hsl(239, 84%, 42%)";
const RING_DIM = "hsl(239, 50%, 76%)";

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

      <div className="flex flex-col-reverse md:flex-row gap-8">
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
                    "flex items-center justify-between w-full text-sm px-3 py-2.5 rounded-lg transition-colors text-left cursor-pointer",
                    isExpanded
                      ? "bg-indigo-50 dark:bg-indigo-950/40"
                      : "hover:bg-muted/50"
                  )}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <span
                      className="h-3 w-3 rounded-full shrink-0 transition-colors"
                      style={{
                        backgroundColor: isExpanded ? RING_ACTIVE : RING_COLOR,
                      }}
                    />
                    <span className={cn("truncate", isExpanded && "font-medium")}>
                      {item.label}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 shrink-0 ml-3">
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
                  <div className="ml-9 mr-1 mt-1 mb-2 space-y-px rounded-lg border bg-muted/30 overflow-hidden">
                    {item.holdings.map((h) => (
                      <div
                        key={h.symbol}
                        className="flex items-center justify-between px-3 py-2 text-xs hover:bg-muted/50"
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="font-medium">{h.symbol}</span>
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

        {/* Donut ring — sticky on desktop */}
        <div className="w-full md:w-56 lg:w-64 shrink-0 self-start md:sticky md:top-4">
          <div className="relative h-56 lg:h-64 [&_.recharts-sector]:outline-none [&_.recharts-pie]:outline-none">
            <ResponsiveContainer width="100%" height="100%">
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

            {/* Center — category title by default, segment info on interaction */}
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
