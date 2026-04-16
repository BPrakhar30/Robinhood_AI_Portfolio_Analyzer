"use client";

import { useState, useRef, useCallback, useMemo } from "react";
import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Play,
  Copy,
  Download,
  ArrowLeft,
  Loader2,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import {
  useMarketNews,
  useEarningsCalendar,
  useEarningsForDate,
} from "@/features/markets/hooks";
import type {
  MarketHeadline,
  RecentDevelopment,
  EarningsEntry,
  EarningsDay,
} from "@/features/markets/types";

// ── Helpers ────────────────────────────────────────────────────────

function timeAgo(isoOrUnix: string): string {
  const now = Date.now();
  const then = new Date(isoOrUnix).getTime();
  const diff = Math.max(0, Math.floor((now - then) / 1000));
  if (diff < 60) return "just now";
  if (diff < 3600) { const m = Math.floor(diff / 60); return `${m} min ago`; }
  if (diff < 86400) { const h = Math.floor(diff / 3600); return `${h}h ago`; }
  const d = Math.floor(diff / 86400);
  return `${d}d ago`;
}

function formatCurrency(n: number | null | undefined): string {
  if (n == null) return "—";
  if (Math.abs(n) >= 1e9) return `US$${(n / 1e9).toFixed(1)}B`;
  if (Math.abs(n) >= 1e6) return `US$${(n / 1e6).toFixed(1)}M`;
  return `US$${n.toFixed(2)}`;
}

function beatLabel(est: number | null, actual: number | null): string {
  if (est == null || actual == null || est === 0) return "—";
  const pct = ((actual - est) / Math.abs(est)) * 100;
  if (pct > 0) return `Beat +${pct.toFixed(2)}%`;
  if (pct < 0) return `Miss ${pct.toFixed(2)}%`;
  return "Inline";
}

function formatDateShort(iso: string): string {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("en-US", { day: "numeric", month: "short" });
}

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

const SOURCE_URLS: Record<string, string> = {
  "CNBC": "https://www.cnbc.com/markets",
  "CNBC Economy": "https://www.cnbc.com/economy",
  "CNBC Earnings": "https://www.cnbc.com/earnings",
  "Reuters": "https://www.reuters.com/markets",
  "Investing.com": "https://www.investing.com/news",
  "Yahoo Finance": "https://finance.yahoo.com",
  "Forbes": "https://www.forbes.com/money",
  "FXStreet": "https://www.fxstreet.com/news",
  "FRED Blog": "https://fredblog.stlouisfed.org",
  "Google News Business": "https://news.google.com/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB",
  "Trading Economics": "https://tradingeconomics.com/news",
  "Bloomberg": "https://www.bloomberg.com/markets",
  "MarketWatch": "https://www.marketwatch.com",
  "Finnhub": "https://finnhub.io",
};

// ── Components ─────────────────────────────────────────────────────

function MarketSummaryItem({ title, summary }: MarketHeadline) {
  const [open, setOpen] = useState(false);

  return (
    <div className="border-b border-border last:border-0">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center justify-between w-full px-4 py-3.5 text-left hover:bg-accent/30 transition-colors cursor-pointer"
      >
        <span className="text-sm font-medium pr-4">{title}</span>
        <ChevronDown
          className={cn(
            "h-4 w-4 text-muted-foreground shrink-0 transition-transform",
            open && "rotate-180"
          )}
        />
      </button>
      {open && (
        <div className="px-4 pb-4 -mt-1">
          <p className="text-xs text-muted-foreground leading-relaxed">
            {summary}
          </p>
          {/* source link removed from accordion — shown globally below */}
        </div>
      )}
    </div>
  );
}

function RecentDevelopmentCard({
  source,
  time_ago: ta,
  title,
  excerpt,
  url,
}: RecentDevelopment) {
  return (
    <a
      href={url || "#"}
      target="_blank"
      rel="noopener noreferrer"
      className="block"
    >
      <Card className="min-w-[280px] max-w-[320px] shrink-0 hover:bg-accent/20 transition-colors cursor-pointer">
        <CardContent className="p-4 space-y-2">
          <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
            <Badge variant="outline" className="text-[10px] px-1.5 py-0 font-normal">
              {source}
            </Badge>
            <span>{ta}</span>
          </div>
          <h4 className="text-sm font-medium leading-snug line-clamp-2">
            {title}
          </h4>
          <p className="text-xs text-muted-foreground leading-relaxed line-clamp-4">
            {excerpt}
          </p>
        </CardContent>
      </Card>
    </a>
  );
}

function RecentDevelopmentsCarousel({
  items,
  updatedAt,
}: {
  items: RecentDevelopment[];
  updatedAt?: string;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [canScrollRight, setCanScrollRight] = useState(true);
  const [canScrollLeft, setCanScrollLeft] = useState(false);

  const checkScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    setCanScrollLeft(el.scrollLeft > 4);
    setCanScrollRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 4);
  }, []);

  const scroll = (dir: "left" | "right") => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollBy({ left: dir === "right" ? 340 : -340, behavior: "smooth" });
    setTimeout(checkScroll, 350);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
          Recent Developments
        </h2>
        {updatedAt && (
          <span className="text-xs text-emerald-600">
            Updated {timeAgo(updatedAt)}
          </span>
        )}
      </div>
      <div className="relative">
        <div
          ref={scrollRef}
          onScroll={checkScroll}
          className="flex gap-3 overflow-hidden -mx-1 px-1"
        >
          {items.map((item, i) => (
            <RecentDevelopmentCard key={i} {...item} />
          ))}
        </div>

        {canScrollLeft && (
          <button
            type="button"
            onClick={() => scroll("left")}
            className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-3 h-8 w-8 rounded-full bg-background border border-border shadow-md flex items-center justify-center hover:bg-accent transition-colors cursor-pointer z-10"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
        )}
        {canScrollRight && (
          <button
            type="button"
            onClick={() => scroll("right")}
            className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-3 h-8 w-8 rounded-full bg-background border border-border shadow-md flex items-center justify-center hover:bg-accent transition-colors cursor-pointer z-10"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}

function EarningsCalendarStrip({
  days,
  selectedDate,
  onSelectDate,
  onWeekShift,
  onToday,
}: {
  days: EarningsDay[];
  selectedDate: string;
  onSelectDate: (date: string) => void;
  onWeekShift: (dir: -1 | 1) => void;
  onToday: () => void;
}) {
  const today = todayISO();

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
          Earnings Calendar
        </h2>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" className="h-7 w-7 cursor-pointer" onClick={() => onWeekShift(-1)}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="sm" className="text-xs h-7 cursor-pointer" onClick={onToday}>
            Today
          </Button>
          <Button variant="ghost" size="icon" className="h-7 w-7 cursor-pointer" onClick={() => onWeekShift(1)}>
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
      <Card>
        <CardContent className="py-2 px-1">
          <div className="flex justify-between">
            {days.map((day) => {
              const selected = day.date === selectedDate;
              const isToday = day.date === today;
              return (
                <button
                  key={day.date}
                  type="button"
                  onClick={() => onSelectDate(day.date)}
                  className={cn(
                    "flex flex-col items-center gap-1 px-3 py-2 rounded-lg transition-colors cursor-pointer min-w-[72px]",
                    selected
                      ? "bg-primary text-primary-foreground"
                      : isToday
                      ? "bg-accent"
                      : "hover:bg-accent/50"
                  )}
                >
                  <span className="text-[11px] font-medium">{day.day_label}</span>
                  <span className={cn("text-xs", selected ? "text-primary-foreground/80" : "text-muted-foreground")}>
                    {formatDateShort(day.date)}
                  </span>
                  <span className={cn("text-[10px]", selected ? "text-primary-foreground/70" : "text-muted-foreground")}>
                    {day.earnings_count > 0 ? `${day.earnings_count} Calls` : "No Calls"}
                  </span>
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function EarningsListItem({
  entry,
  onSelect,
}: {
  entry: EarningsEntry;
  onSelect: (e: EarningsEntry) => void;
}) {
  const hasBeat = entry.eps_actual != null && entry.eps_estimate != null;

  return (
    <Card
      className="hover:bg-accent/20 transition-colors cursor-pointer"
      onClick={() => onSelect(entry)}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between mb-2">
          <div>
            <p className="text-sm font-semibold">{entry.company}</p>
            <p className="text-xs text-muted-foreground">{entry.symbol}</p>
          </div>
          <div className="text-right">
            <Badge variant="outline" className="text-[10px] px-1.5 py-0">
              Q{entry.quarter} {entry.year}
            </Badge>
            <p className="text-[10px] text-muted-foreground mt-0.5">{entry.hour}</p>
          </div>
        </div>

        {hasBeat && (
          <div className="flex gap-4 text-xs">
            <div>
              <span className="text-muted-foreground">EPS Est:</span>{" "}
              <span className="font-medium">US${entry.eps_estimate?.toFixed(2)}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Actual:</span>{" "}
              <span className="font-medium">US${entry.eps_actual?.toFixed(2)}</span>
            </div>
            <div className={cn(
              "font-medium",
              (entry.eps_actual ?? 0) >= (entry.eps_estimate ?? 0) ? "text-emerald-600" : "text-red-500"
            )}>
              {beatLabel(entry.eps_estimate, entry.eps_actual)}
            </div>
          </div>
        )}

        {!hasBeat && (
          <p className="text-xs text-muted-foreground">
            {entry.eps_estimate != null
              ? `EPS Estimate: US$${entry.eps_estimate.toFixed(2)}`
              : "Estimates pending"}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function EarningsDetailView({
  entry,
  onBack,
}: {
  entry: EarningsEntry;
  onBack: () => void;
}) {
  const [activeTab, setActiveTab] = useState<"highlights" | "transcript" | "documents">("highlights");

  const revBeat = beatLabel(entry.revenue_estimate, entry.revenue_actual);
  const epsBeat = beatLabel(entry.eps_estimate, entry.eps_actual);

  return (
    <div className="space-y-4">
      <Button
        variant="ghost"
        size="sm"
        className="gap-1 -ml-2 cursor-pointer"
        onClick={onBack}
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back to calendar
      </Button>

      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-lg font-semibold">
            {entry.symbol} Q{entry.quarter} {entry.year} Earnings Call
          </h2>
          <p className="text-xs text-muted-foreground">
            {entry.date}, {entry.hour}
          </p>
        </div>
        <Button variant="outline" size="sm" className="gap-1.5 cursor-pointer opacity-50 pointer-events-none" tabIndex={-1}>
          <Play className="h-3.5 w-3.5" />
          Listen
        </Button>
      </div>

      {/* Estimates vs Actual table */}
      <Card>
        <CardContent className="p-0">
          <div className="grid grid-cols-4 text-xs">
            <div className="p-3 border-b border-r border-border" />
            <div className="p-3 border-b border-r border-border text-right text-muted-foreground font-medium">
              Estimate
            </div>
            <div className="p-3 border-b border-r border-border text-right font-medium">
              Actual
            </div>
            <div className="p-3 border-b border-border text-right font-medium" />

            <div className="p-3 border-b border-r border-border font-medium">Revenue</div>
            <div className="p-3 border-b border-r border-border text-right text-muted-foreground">
              {formatCurrency(entry.revenue_estimate)}
            </div>
            <div className="p-3 border-b border-r border-border text-right font-medium">
              {formatCurrency(entry.revenue_actual)}
            </div>
            <div className={cn(
              "p-3 border-b border-border text-right font-medium",
              revBeat.startsWith("Beat") ? "text-emerald-600" : revBeat.startsWith("Miss") ? "text-red-500" : "text-muted-foreground"
            )}>
              {revBeat}
            </div>

            <div className="p-3 border-r border-border font-medium">EPS (Adj.)</div>
            <div className="p-3 border-r border-border text-right text-muted-foreground">
              {entry.eps_estimate != null ? `US$${entry.eps_estimate.toFixed(2)}` : "—"}
            </div>
            <div className="p-3 border-r border-border text-right font-medium">
              {entry.eps_actual != null ? `US$${entry.eps_actual.toFixed(2)}` : "—"}
            </div>
            <div className={cn(
              "p-3 text-right font-medium",
              epsBeat.startsWith("Beat") ? "text-emerald-600" : epsBeat.startsWith("Miss") ? "text-red-500" : "text-muted-foreground"
            )}>
              {epsBeat}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Detail tabs */}
      <div>
        <div className="flex items-center justify-between border-b border-border">
          <div className="flex">
            {(["highlights", "transcript", "documents"] as const).map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={cn(
                  "px-4 py-2 text-sm font-medium transition-colors cursor-pointer capitalize",
                  activeTab === tab
                    ? "text-foreground border-b-2 border-primary"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                {tab === "highlights" ? "Highlights" : tab === "transcript" ? "Transcript" : "Documents"}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-1 pr-2">
            <Button variant="ghost" size="icon" className="h-7 w-7 cursor-pointer">
              <Copy className="h-3.5 w-3.5" />
            </Button>
            <Button variant="ghost" size="icon" className="h-7 w-7 cursor-pointer">
              <Download className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>

        <div className="pt-4">
          {activeTab === "highlights" && (
            <div className="text-center py-10">
              <p className="text-sm text-muted-foreground">
                AI-generated highlights will appear here once the LLM pipeline is connected.
              </p>
            </div>
          )}
          {activeTab === "transcript" && (
            <div className="text-center py-10">
              <p className="text-sm text-muted-foreground">
                Transcript will be generated using AI when available.
              </p>
            </div>
          )}
          {activeTab === "documents" && (
            <div className="text-center py-10">
              <p className="text-sm text-muted-foreground">
                SEC filings and press releases will appear here when available.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center py-16">
      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────

export default function MarketsPage() {
  const [activeSection, setActiveSection] = useState<"news" | "earnings">("news");
  const [weekOffset, setWeekOffset] = useState(0);
  const [selectedDate, setSelectedDate] = useState(todayISO());
  const [selectedEarnings, setSelectedEarnings] = useState<EarningsEntry | null>(null);

  const calendarCenterDate = useMemo(() => {
    const d = new Date();
    d.setDate(d.getDate() + weekOffset * 7);
    return d.toISOString().slice(0, 10);
  }, [weekOffset]);

  const { data: newsData, isLoading: newsLoading } = useMarketNews();
  const { data: calendarData, isLoading: calLoading } = useEarningsCalendar(calendarCenterDate);
  const { data: earningsData, isLoading: earningsLoading } = useEarningsForDate(selectedDate);

  const headlines: MarketHeadline[] = newsData?.summary?.headlines ?? [];
  const developments: RecentDevelopment[] = newsData?.developments?.articles ?? [];
  const updatedAt = newsData?.summary?.updated_at;
  const apiSources: string[] = newsData?.sources ?? [];

  const calendarDays: EarningsDay[] = calendarData?.week ?? [];
  const earningsEntries: EarningsEntry[] = earningsData?.entries ?? [];

  const liveSources = useMemo(() => {
    if (apiSources.length > 0) return apiSources;
    const seen = new Set<string>();
    for (const h of headlines) {
      if (h.source) seen.add(h.source);
    }
    return Array.from(seen);
  }, [apiSources, headlines]);

  return (
    <div className="space-y-6">
      {/* Header with tabs */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Markets</h1>
          <p className="text-sm text-muted-foreground">
            Market news, earnings calendar, and macro developments.
          </p>
        </div>
        <div className="flex rounded-lg bg-muted p-0.5">
          {(["news", "earnings"] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => {
                setActiveSection(tab);
                setSelectedEarnings(null);
              }}
              className={cn(
                "px-4 py-1.5 text-sm font-medium rounded-md transition-colors cursor-pointer capitalize",
                activeSection === tab
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* ── News section ────────────────────────────────────────── */}
      {activeSection === "news" && (
        <>
          {newsLoading ? (
            <LoadingSpinner />
          ) : (
            <>
              {/* Market Summary */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
                    Market Summary
                  </h2>
                  {updatedAt && (
                    <span className="text-xs text-emerald-600">
                      Updated {timeAgo(updatedAt)}
                    </span>
                  )}
                </div>
                {headlines.length > 0 ? (
                  <Card>
                    <CardContent className="p-0">
                      {headlines.map((item, i) => (
                        <MarketSummaryItem key={i} {...item} />
                      ))}
                    </CardContent>
                  </Card>
                ) : (
                  <Card>
                    <CardContent className="py-10 text-center">
                      <p className="text-sm text-muted-foreground">
                        No market headlines available right now. Check back shortly.
                      </p>
                    </CardContent>
                  </Card>
                )}
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1 mt-3">
                  {liveSources.map((name) => (
                    <a
                      key={name}
                      href={SOURCE_URLS[name] ?? "#"}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {name}
                      <ExternalLink className="h-2.5 w-2.5" />
                    </a>
                  ))}
                  <span className="text-[11px] text-muted-foreground ml-1">
                    · {liveSources.length} sources
                  </span>
                </div>
              </div>

              <Separator />

              {/* Recent Developments */}
              {developments.length > 0 ? (
                <RecentDevelopmentsCarousel items={developments} updatedAt={updatedAt} />
              ) : (
                <div>
                  <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground mb-3">
                    Recent Developments
                  </h2>
                  <Card>
                    <CardContent className="py-10 text-center">
                      <p className="text-sm text-muted-foreground">
                        No recent developments to display.
                      </p>
                    </CardContent>
                  </Card>
                </div>
              )}
            </>
          )}
        </>
      )}

      {/* ── Earnings section ────────────────────────────────────── */}
      {activeSection === "earnings" && (
        <>
          {selectedEarnings ? (
            <EarningsDetailView
              entry={selectedEarnings}
              onBack={() => setSelectedEarnings(null)}
            />
          ) : (
            <>
              {calLoading ? (
                <LoadingSpinner />
              ) : (
                <EarningsCalendarStrip
                  days={calendarDays}
                  selectedDate={selectedDate}
                  onSelectDate={setSelectedDate}
                  onWeekShift={(dir) => setWeekOffset((p) => p + dir)}
                  onToday={() => {
                    setWeekOffset(0);
                    setSelectedDate(todayISO());
                  }}
                />
              )}

              {/* Earnings list */}
              {earningsLoading ? (
                <LoadingSpinner />
              ) : earningsEntries.length > 0 ? (
                <div className="space-y-3">
                  {earningsEntries.map((entry, i) => (
                    <EarningsListItem
                      key={`${entry.symbol}-${i}`}
                      entry={entry}
                      onSelect={setSelectedEarnings}
                    />
                  ))}
                </div>
              ) : (
                <Card>
                  <CardContent className="py-10 text-center">
                    <p className="text-sm text-muted-foreground">
                      No earnings calls scheduled for {formatDateShort(selectedDate)}.
                    </p>
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
