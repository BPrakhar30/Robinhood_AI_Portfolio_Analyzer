"use client";

import { useState } from "react";
import React from "react";
import {
  Activity,
  ArrowDown,
  ArrowUp,
  BarChart3,
  BookOpen,
  ChevronDown,
  ChevronUp,
  DollarSign,
  Droplets,
  Flame,
  Globe,
  Minus,
  Shield,
  Sparkles,
  TrendingUp,
  Zap,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { useMacroPulse } from "@/features/macro/hooks";
import type { MacroIndicator, PortfolioExposure, Signal } from "@/features/macro/types";

const INDICATOR_ICONS: Record<string, React.ElementType> = {
  vix: Zap,
  us10y: BarChart3,
  sp500: TrendingUp,
  nasdaq: Activity,
  dxy: DollarSign,
  oil: Droplets,
  hyg: Shield,
  gold: Flame,
};

const SIGNAL_STYLES: Record<Signal, { dot: string; bg: string; text: string; border: string }> = {
  bullish: {
    dot: "bg-emerald-500",
    bg: "bg-emerald-500/10",
    text: "text-emerald-700 dark:text-emerald-400",
    border: "border-emerald-500/30",
  },
  bearish: {
    dot: "bg-red-500",
    bg: "bg-red-500/10",
    text: "text-red-700 dark:text-red-400",
    border: "border-red-500/30",
  },
  caution: {
    dot: "bg-amber-500",
    bg: "bg-amber-500/10",
    text: "text-amber-700 dark:text-amber-400",
    border: "border-amber-500/30",
  },
  neutral: {
    dot: "bg-zinc-400",
    bg: "bg-zinc-500/10",
    text: "text-muted-foreground",
    border: "border-border",
  },
};

// ── Zone 1: Traffic Light Summary ────────────────────────────────────

function SignalCard({ indicator }: { indicator: MacroIndicator }) {
  const Icon = INDICATOR_ICONS[indicator.key] || Activity;
  const style = SIGNAL_STYLES[indicator.signal];
  const isPositive = indicator.change !== null && indicator.change > 0;
  const ChangeIcon = indicator.change === null
    ? Minus
    : isPositive
    ? ArrowUp
    : ArrowDown;

  return (
    <Card className={cn("transition-all hover:shadow-md", style.border)}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <div className={cn("rounded-lg p-2", style.bg)}>
              <Icon className={cn("h-4 w-4", style.text)} />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">{indicator.label}</p>
              <p className="text-lg font-semibold tabular-nums leading-tight">
                {indicator.display_value}
              </p>
            </div>
          </div>
          <div className="text-right shrink-0">
            <div className={cn(
              "inline-flex items-center gap-0.5 text-xs font-medium tabular-nums",
              isPositive ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400",
              indicator.change === null && "text-muted-foreground",
            )}>
              <ChangeIcon className="h-3 w-3" />
              {indicator.change_display}
            </div>
            <div className="mt-1">
              <Badge
                variant="outline"
                className={cn("text-[10px] px-1.5 py-0 font-normal", style.text, style.border)}
              >
                <span className={cn("inline-block h-1.5 w-1.5 rounded-full mr-1", style.dot)} />
                {indicator.signal_label}
              </Badge>
            </div>
          </div>
        </div>
        <p className="text-[11px] text-muted-foreground mt-2 leading-relaxed">
          {indicator.portfolio_impact || indicator.description}
        </p>
      </CardContent>
    </Card>
  );
}

function SignalCardSkeleton() {
  return (
    <Card>
      <CardContent className="p-4 space-y-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2.5">
            <Skeleton className="h-8 w-8 rounded-lg" />
            <div className="space-y-1.5">
              <Skeleton className="h-3 w-16" />
              <Skeleton className="h-5 w-20" />
            </div>
          </div>
          <div className="space-y-1.5 text-right">
            <Skeleton className="h-3 w-12 ml-auto" />
            <Skeleton className="h-4 w-16 ml-auto" />
          </div>
        </div>
        <Skeleton className="h-3 w-full" />
      </CardContent>
    </Card>
  );
}

// ── Zone 2: Portfolio Exposure ────────────────────────────────────────

const MAX_CHIPS = 5;

function ExposureBar({
  label,
  pct,
  color,
  symbols,
}: {
  label: string;
  pct: number;
  color: string;
  symbols?: string[];
}) {
  const [expanded, setExpanded] = React.useState(false);
  const shown = symbols ?? [];
  const overflow = shown.length > MAX_CHIPS;
  const visible = expanded ? shown : shown.slice(0, MAX_CHIPS);

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium tabular-nums">{pct.toFixed(0)}%</span>
      </div>
      <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all duration-700", color)}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
      {shown.length > 0 ? (
        <div className="flex flex-wrap items-center gap-1 pt-0.5">
          {visible.map((sym) => (
            <span
              key={sym}
              className="inline-block rounded px-1.5 py-0.5 text-[10px] font-medium bg-muted text-muted-foreground"
            >
              {sym}
            </span>
          ))}
          {overflow && !expanded && (
            <button
              onClick={() => setExpanded(true)}
              className="text-[10px] font-medium text-amber-600 dark:text-amber-400 hover:underline"
            >
              +{shown.length - MAX_CHIPS} more
            </button>
          )}
          {overflow && expanded && (
            <button
              onClick={() => setExpanded(false)}
              className="text-[10px] font-medium text-muted-foreground/70 hover:underline"
            >
              show less
            </button>
          )}
        </div>
      ) : (
        <p className="text-[10px] text-muted-foreground/50 italic">None in your portfolio</p>
      )}
    </div>
  );
}

function PortfolioExposureSection({ exposure }: { exposure: PortfolioExposure }) {
  const syms = exposure.symbols_by_category ?? {};
  return (
    <Card>
      <CardContent className="p-5 sm:p-6">
        <div className="flex items-center gap-2 mb-5">
          <div className="rounded-lg p-2 bg-amber-500/10">
            <Globe className="h-4 w-4 text-amber-600 dark:text-amber-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold">Your Portfolio's Macro Exposure</h3>
            <p className="text-xs text-muted-foreground">
              How the macro environment connects to your {exposure.total_positions} positions
              {exposure.total_market_value > 0 && (
                <> &middot; ${exposure.total_market_value.toLocaleString(undefined, { maximumFractionDigits: 0 })}</>
              )}
            </p>
          </div>
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          <ExposureBar label="Rate-Sensitive" pct={exposure.rate_sensitive_pct} color="bg-red-500" symbols={syms.rate_sensitive} />
          <ExposureBar label="Growth Stocks" pct={exposure.growth_pct} color="bg-violet-500" symbols={syms.growth} />
          <ExposureBar label="Cyclical" pct={exposure.cyclical_pct} color="bg-amber-500" symbols={syms.cyclical} />
          <ExposureBar label="Defensive" pct={exposure.defensive_pct} color="bg-emerald-500" symbols={syms.defensive} />
          <ExposureBar label="International Revenue" pct={exposure.international_revenue_pct} color="bg-blue-500" symbols={syms.international_revenue} />
          <ExposureBar label="Energy" pct={exposure.energy_pct} color="bg-orange-500" symbols={syms.energy} />
        </div>

        <p className="mt-4 text-[11px] text-muted-foreground/60 leading-relaxed">
          A holding can appear in multiple categories because each category measures a different type of macro risk.
          For example, a tech stock may be rate-sensitive, cyclical, and growth-oriented at the same time.
          Broad-market ETFs (e.g. SPY, VOO) are not assigned to a specific category.
        </p>
      </CardContent>
    </Card>
  );
}

// ── Zone 3: Indicator Details ────────────────────────────────────────

function IndicatorDetailCard({ indicator }: { indicator: MacroIndicator }) {
  const [expanded, setExpanded] = useState(false);
  const Icon = INDICATOR_ICONS[indicator.key] || Activity;
  const style = SIGNAL_STYLES[indicator.signal];
  const isPositive = indicator.change !== null && indicator.change > 0;

  return (
    <Card className={cn("transition-all", expanded && "ring-1 ring-amber-500/30")}>
      <CardContent className="p-0">
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="w-full p-4 sm:p-5 flex items-center gap-4 text-left cursor-pointer hover:bg-accent/30 transition-colors"
        >
          <div className={cn("rounded-lg p-2.5 shrink-0", style.bg)}>
            <Icon className={cn("h-5 w-5", style.text)} />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="text-sm font-semibold">{indicator.label}</h4>
              <Badge
                variant="outline"
                className={cn("text-[10px] px-1.5 py-0 font-normal", style.text, style.border)}
              >
                <span className={cn("inline-block h-1.5 w-1.5 rounded-full mr-1", style.dot)} />
                {indicator.signal_label}
              </Badge>
              {indicator.category !== "essential" && (
                <Badge variant="secondary" className="text-[10px] px-1.5 py-0 font-normal capitalize">
                  {indicator.category}
                </Badge>
              )}
            </div>
            <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{indicator.description}</p>
          </div>

          <div className="text-right shrink-0 mr-2">
            <p className="text-lg font-semibold tabular-nums">{indicator.display_value}</p>
            <p className={cn(
              "text-xs font-medium tabular-nums",
              isPositive ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400",
              indicator.change === null && "text-muted-foreground",
            )}>
              {indicator.change_display}
            </p>
          </div>

          {expanded
            ? <ChevronUp className="h-4 w-4 text-muted-foreground shrink-0" />
            : <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />}
        </button>

        {expanded && (
          <div className="px-4 sm:px-5 pb-4 sm:pb-5 space-y-3 border-t border-border pt-4">
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">
                What this means
              </p>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {indicator.detail || indicator.description}
              </p>
            </div>
            <Separator />
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">
                Impact on your portfolio
              </p>
              <p className="text-sm leading-relaxed">
                {indicator.portfolio_impact || "Connect holdings to see personalized impact."}
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── AI Summary ───────────────────────────────────────────────────────

function AiSummaryBanner({ summary }: { summary: string }) {
  return (
    <Card className="border-amber-500/30 bg-amber-500/5">
      <CardContent className="p-4 sm:p-5">
        <div className="flex gap-3">
          <div className="rounded-lg p-2 bg-amber-500/15 h-fit shrink-0">
            <Sparkles className="h-4 w-4 text-amber-600 dark:text-amber-400" />
          </div>
          <div>
            <p className="text-xs font-medium text-amber-700 dark:text-amber-400 uppercase tracking-wider mb-1">
              AI Macro Briefing
            </p>
            <p className="text-sm leading-relaxed">{summary}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Alerts Banner ────────────────────────────────────────────────────

function AlertsBanner({ alerts }: { alerts: Array<{ severity: string; title: string; message: string }> }) {
  if (alerts.length === 0) return null;

  return (
    <div className="space-y-2">
      {alerts.map((alert, i) => (
        <Card
          key={i}
          className={cn(
            "border-l-[3px]",
            alert.severity === "critical"
              ? "border-l-red-500 bg-red-500/5"
              : "border-l-amber-500 bg-amber-500/5",
          )}
        >
          <CardContent className="p-3 sm:p-4">
            <p className={cn(
              "text-sm font-medium",
              alert.severity === "critical" ? "text-red-700 dark:text-red-400" : "text-amber-700 dark:text-amber-400",
            )}>
              {alert.title}
            </p>
            <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
              {alert.message}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ── Detailed AI Summary ──────────────────────────────────────────────

function renderMarkdownLine(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

/**
 * Parse the LLM markdown into a flat sequence of typed tokens.
 * The LLM sometimes puts a ## header and its body on consecutive
 * single-spaced lines (no blank line separator), so we can't rely on
 * double-newline block splitting. Instead we tokenise line-by-line.
 */
type Token =
  | { type: "heading"; text: string }
  | { type: "bullet"; text: string }
  | { type: "paragraph"; text: string };

function tokenise(content: string): Token[] {
  const tokens: Token[] = [];
  const lines = content.split(/\n/);

  for (const raw of lines) {
    const line = raw.trim();
    if (!line) continue;

    const headingMatch = line.match(/^#{1,3}\s+(.+)/);
    if (headingMatch) {
      tokens.push({ type: "heading", text: headingMatch[1].replace(/\*\*/g, "") });
      continue;
    }

    const bulletMatch = line.match(/^[•\-*]\s+(.+)/);
    if (bulletMatch) {
      tokens.push({ type: "bullet", text: bulletMatch[1] });
      continue;
    }

    // Merge consecutive paragraph lines into the previous paragraph token
    if (tokens.length > 0 && tokens[tokens.length - 1].type === "paragraph") {
      (tokens[tokens.length - 1] as { type: "paragraph"; text: string }).text += " " + line;
    } else {
      tokens.push({ type: "paragraph", text: line });
    }
  }

  return tokens;
}

function DetailedSummarySection({ content }: { content: string }) {
  const tokens = tokenise(content);

  return (
    <Card className="border-amber-500/20">
      <CardContent className="p-5 sm:p-7">
        <div className="flex items-center gap-2.5 mb-5">
          <div className="rounded-lg p-2 bg-amber-500/10">
            <BookOpen className="h-5 w-5 text-amber-600 dark:text-amber-400" />
          </div>
          <div>
            <h3 className="text-base font-semibold">AI Macro Summary</h3>
            <p className="text-xs text-muted-foreground">
              Comprehensive analysis connecting macro conditions to your portfolio
            </p>
          </div>
        </div>

        <div className="space-y-3 text-sm leading-relaxed">
          {tokens.map((token, i) => {
            if (token.type === "heading") {
              return (
                <h4 key={i} className="text-sm font-semibold text-foreground pt-3 first:pt-0 border-t border-border/50 first:border-0">
                  {token.text}
                </h4>
              );
            }
            if (token.type === "bullet") {
              return (
                <div key={i} className="flex gap-2.5">
                  <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-amber-500 shrink-0" />
                  <span className="text-muted-foreground">{renderMarkdownLine(token.text)}</span>
                </div>
              );
            }
            return (
              <p key={i} className="text-muted-foreground">
                {renderMarkdownLine(token.text)}
              </p>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Loading skeleton ─────────────────────────────────────────────────

function MacroPulseSkeleton() {
  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <Skeleton className="h-7 w-64" />
        <Skeleton className="h-4 w-96" />
      </div>
      <Skeleton className="h-20 w-full rounded-xl" />
      <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <SignalCardSkeleton key={i} />
        ))}
      </div>
      <Skeleton className="h-48 w-full rounded-xl" />
      <div className="space-y-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-20 w-full rounded-xl" />
        ))}
      </div>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────

export default function MacroPulsePage() {
  const { data, isLoading } = useMacroPulse();

  if (isLoading || !data) {
    return (
      <div className="space-y-6 px-1">
        <MacroPulseSkeleton />
      </div>
    );
  }

  const essential = data.indicators.filter((i) => i.category === "essential");
  const secondary = data.indicators.filter((i) => i.category !== "essential");
  const allIndicators = [...essential, ...secondary];

  return (
    <div className="space-y-8 px-1">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold tracking-tight sm:text-2xl flex items-center gap-2">
          <Activity className="h-6 w-6 text-amber-600 dark:text-amber-400" />
          Macro Pulse
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          How the macro environment is affecting your portfolio right now.
          Indicators are personalized based on your {data.exposure.total_positions} positions.
        </p>
      </div>

      {/* Active alerts */}
      {data.alerts.length > 0 && <AlertsBanner alerts={data.alerts} />}

      {/* AI Summary */}
      {data.ai_summary && <AiSummaryBanner summary={data.ai_summary} />}

      {/* Zone 1: Traffic Light Cards */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
            Market Signals
          </h2>
          <Badge variant="outline" className="text-[10px] px-1.5 py-0 font-normal">
            {essential.length} essential
          </Badge>
        </div>
        <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {essential.map((ind) => (
            <SignalCard key={ind.key} indicator={ind} />
          ))}
        </div>
      </div>

      {/* Zone 2: Portfolio Exposure */}
      <PortfolioExposureSection exposure={data.exposure} />

      {/* Zone 3: All Indicators Detail */}
      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3">
          Indicator Details
        </h2>
        <div className="space-y-2">
          {allIndicators.map((ind) => (
            <IndicatorDetailCard key={ind.key} indicator={ind} />
          ))}
        </div>
      </div>

      {/* Detailed AI Summary at bottom */}
      {data.detailed_summary && (
        <DetailedSummarySection content={data.detailed_summary} />
      )}

      {/* Footer timestamp */}
      <p className="text-[11px] text-muted-foreground text-center pb-4">
        Last updated: {new Date(data.updated_at).toLocaleString()}
      </p>
    </div>
  );
}
