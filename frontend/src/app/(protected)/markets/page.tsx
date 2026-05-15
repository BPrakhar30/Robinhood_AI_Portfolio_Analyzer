"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ChevronDown,
  ExternalLink,
  Search,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { useMarketNews } from "@/features/markets/hooks";
import type {
  MarketHeadline,
  MarketSource,
} from "@/features/markets/types";
import {
  usePortfolioNews,
  useStockUniverse,
} from "@/features/stocks/hooks";
import type {
  StockCard as StockCardType,
  StockNewsItem,
} from "@/features/stocks/types";

// ── Helpers ────────────────────────────────────────────────────────

function timeAgo(isoOrUnix: string): string {
  const now = Date.now();
  const then = new Date(isoOrUnix).getTime();
  const diff = Math.max(0, Math.floor((now - then) / 1000));
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function formatPrice(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—";
  return n.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatPercent(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}%`;
}

// ── Market Summary item ────────────────────────────────────────────

function MarketSummaryItem({
  title,
  summary,
  ai_summary,
  source,
  url,
}: MarketHeadline) {
  const [open, setOpen] = useState(false);
  const body = ai_summary?.trim() || summary?.trim() || "";

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
            open && "rotate-180",
          )}
        />
      </button>
      {open && (
        <div className="px-4 pb-4 -mt-1 space-y-2">
          {body ? (
            <p className="text-xs text-muted-foreground leading-relaxed">
              {body}
            </p>
          ) : (
            <p className="text-xs text-muted-foreground italic">
              Generating AI summary…
            </p>
          )}
          {(source || url) && (
            <div className="flex items-center gap-2 pt-1">
              {source && (
                <Badge variant="outline" className="text-[10px] px-1.5 py-0 font-normal">
                  {source}
                </Badge>
              )}
              {url && (
                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors"
                >
                  Read full article
                  <ExternalLink className="h-2.5 w-2.5" />
                </a>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Portfolio News grid ────────────────────────────────────────────

const FILLER_BULLET_PATTERNS = [
  /read (the )?full/i,
  /for more (context|details|info)/i,
  /click (through|here)/i,
  /details? pending/i,
  /story (is )?developing/i,
  /more to come/i,
  /to be (confirmed|determined|announced)/i,
  /is relevant to .* based on recent market coverage/i,
];

const LEADING_BULLET_RE = /^[\u2022\u2023\u25E6\u2043\-\*\s]+/;
const LEADING_NUMBER_RE = /^\d+[\.\)]\s*/;

function stripBullet(line: string): string {
  return line.replace(LEADING_BULLET_RE, "").replace(LEADING_NUMBER_RE, "").trim();
}

function isFiller(line: string): boolean {
  return FILLER_BULLET_PATTERNS.some((re) => re.test(line));
}

function summaryPoints(item: StockNewsItem): string[] {
  const raw = (item.ai_summary?.trim() || item.summary?.trim() || item.headline)
    .replace(/\r/g, "")
    .trim();

  let lines: string[] = [];
  for (const rawLine of raw.split(/\n+/)) {
    for (const part of rawLine.split(/\s*[•]\s*/)) {
      const cleaned = stripBullet(part);
      if (cleaned) lines.push(cleaned);
    }
  }

  if (lines.length < 2) {
    const flat = raw.replace(/\s+/g, " ");
    lines = flat
      .split(/(?<=[.!?])\s+/)
      .map((s) => stripBullet(s))
      .filter(Boolean);
  }

  const seen = new Set<string>();
  const headlineKey = item.headline.trim().toLowerCase();
  const cleaned: string[] = [];

  for (const line of lines) {
    let text = line
      .replace(/\s+/g, " ")
      .trim()
      .replace(/([.!?])\.+$/, "$1");
    if (!text) continue;
    if (isFiller(text)) continue;
    if (!text.endsWith(".") && !text.endsWith("!") && !text.endsWith("?")) {
      text += ".";
    }
    const key = text.replace(/[.!?]+$/, "").toLowerCase();
    if (key === headlineKey.replace(/[.!?]+$/, "")) continue;
    if (seen.has(key)) continue;
    seen.add(key);
    cleaned.push(text);
    if (cleaned.length === 3) break;
  }

  return cleaned;
}

type SentimentFilter = "all" | "positive" | "negative";

function PortfolioNewsCard({ item }: { item: StockNewsItem }) {
  const points = summaryPoints(item);
  const sentimentColor = item.sentiment === "negative"
    ? "border-l-red-500"
    : item.sentiment === "positive"
    ? "border-l-emerald-500"
    : "border-l-transparent";

  return (
    <a
      href={item.url}
      target="_blank"
      rel="noopener noreferrer"
      className="group block h-full"
    >
      <Card className={cn(
        "h-full flex flex-col hover:bg-accent/20 hover:border-amber-500/40 transition-colors cursor-pointer border-l-[3px]",
        sentimentColor,
      )}>
        <CardContent className="p-4 flex-1 flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
            {item.symbol && (
              <Badge className="text-[10px] px-1.5 py-0 font-medium bg-amber-500/15 text-amber-700 dark:text-amber-300 hover:bg-amber-500/25 border-transparent">
                {item.symbol}
              </Badge>
            )}
            {item.sentiment && item.sentiment !== "neutral" && (
              <Badge
                variant="outline"
                className={cn(
                  "text-[10px] px-1.5 py-0 font-normal",
                  item.sentiment === "negative"
                    ? "text-red-600 dark:text-red-400 border-red-500/30"
                    : "text-emerald-600 dark:text-emerald-400 border-emerald-500/30",
                )}
              >
                {item.sentiment === "negative" ? "Risk" : "Positive"}
              </Badge>
            )}
            <span className="ml-auto">{item.time_ago}</span>
          </div>
          <h4 className="text-sm font-semibold leading-snug line-clamp-2 group-hover:text-foreground transition-colors">
            {item.headline}
          </h4>
          {points.length > 0 ? (
            <ul className="space-y-2 text-xs text-muted-foreground leading-relaxed flex-1">
              {points.map((point, idx) => {
                const isImpact = idx === points.length - 1 && points.length === 3;
                return (
                  <li key={idx} className="flex gap-2">
                    <span className={cn(
                      "mt-1.5 h-1.5 w-1.5 rounded-full shrink-0",
                      isImpact && item.sentiment === "negative"
                        ? "bg-red-500"
                        : isImpact && item.sentiment === "positive"
                        ? "bg-emerald-500"
                        : "bg-amber-500",
                    )} />
                    <span className={cn(
                      isImpact && "text-foreground font-medium",
                    )}>
                      {point}
                    </span>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="text-xs text-muted-foreground italic flex-1">
              Generating summary…
            </p>
          )}
          <div className="pt-1 inline-flex items-center gap-1 text-[11px] text-muted-foreground group-hover:text-amber-600 dark:group-hover:text-amber-400 transition-colors">
            Read full article
            <ExternalLink className="h-2.5 w-2.5" />
          </div>
        </CardContent>
      </Card>
    </a>
  );
}

const PORTFOLIO_NEWS_INITIAL = 9;

function PortfolioNewsGrid({
  articles,
  updatedAt,
}: {
  articles: StockNewsItem[];
  updatedAt?: string;
}) {
  const [showAll, setShowAll] = useState(false);
  const [filter, setFilter] = useState<SentimentFilter>("all");

  const filtered = useMemo(() => {
    if (filter === "all") return articles;
    return articles.filter((a) => a.sentiment === filter);
  }, [articles, filter]);

  const riskCount = articles.filter((a) => a.sentiment === "negative").length;
  const positiveCount = articles.filter((a) => a.sentiment === "positive").length;

  const visible = showAll ? filtered : filtered.slice(0, PORTFOLIO_NEWS_INITIAL);
  const hasMore = filtered.length > PORTFOLIO_NEWS_INITIAL;

  if (!articles.length) return null;

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-3">
        <div className="flex items-baseline gap-2">
          <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
            Portfolio News
          </h2>
          <span className="text-[11px] text-muted-foreground">
            {filtered.length} {filtered.length === 1 ? "story" : "stories"} across your holdings
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center rounded-lg border border-border p-0.5">
            <button
              type="button"
              onClick={() => { setFilter("all"); setShowAll(false); }}
              className={cn(
                "px-3 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer",
                filter === "all"
                  ? "bg-accent text-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              All
            </button>
            <button
              type="button"
              onClick={() => { setFilter("negative"); setShowAll(false); }}
              className={cn(
                "px-3 py-1 text-xs font-medium rounded-md transition-colors flex items-center gap-1 cursor-pointer",
                filter === "negative"
                  ? "bg-red-500/10 text-red-600 dark:text-red-400"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              <AlertTriangle className="h-3 w-3" />
              Risks {riskCount > 0 && <span className="text-[10px]">({riskCount})</span>}
            </button>
            <button
              type="button"
              onClick={() => { setFilter("positive"); setShowAll(false); }}
              className={cn(
                "px-3 py-1 text-xs font-medium rounded-md transition-colors flex items-center gap-1 cursor-pointer",
                filter === "positive"
                  ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              <ShieldCheck className="h-3 w-3" />
              Positives {positiveCount > 0 && <span className="text-[10px]">({positiveCount})</span>}
            </button>
          </div>
          {updatedAt && (
            <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />
              Updated {timeAgo(updatedAt)}
            </span>
          )}
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="py-8 text-center">
          <p className="text-sm text-muted-foreground">
            No {filter === "negative" ? "risk" : "positive"} news for your holdings right now.
          </p>
        </div>
      ) : (
        <div className="grid gap-3 grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
          {visible.map((a, i) => (
            <PortfolioNewsCard key={`${a.url}-${i}`} item={a} />
          ))}
        </div>
      )}

      {hasMore && (
        <div className="mt-4 flex justify-center">
          <button
            type="button"
            onClick={() => setShowAll((v) => !v)}
            className="inline-flex items-center gap-1.5 px-4 py-1.5 text-xs font-medium rounded-md border border-border text-muted-foreground hover:text-foreground hover:border-amber-500/40 hover:bg-amber-500/5 transition-colors cursor-pointer"
          >
            {showAll ? "Show less" : `Show all ${filtered.length} stories`}
          </button>
        </div>
      )}
    </div>
  );
}

// ── Stocks tab ─────────────────────────────────────────────────────

function StockLogo({ card }: { card: StockCardType }) {
  const [failed, setFailed] = useState(false);
  if (!card.logo || failed) {
    return (
      <div className="h-9 w-9 rounded-lg border border-border bg-muted flex items-center justify-center text-[11px] font-semibold text-muted-foreground shrink-0">
        {card.symbol.slice(0, 2)}
      </div>
    );
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={card.logo}
      alt={`${card.name} logo`}
      className="h-9 w-9 rounded-lg border border-border object-contain bg-white shrink-0"
      onError={() => setFailed(true)}
    />
  );
}

function StockRow({ card }: { card: StockCardType }) {
  const up = (card.change_percent ?? 0) > 0;
  const down = (card.change_percent ?? 0) < 0;
  return (
    <Link
      href={`/markets/${encodeURIComponent(card.symbol)}`}
      className="block h-full"
    >
      <Card className="h-full hover:bg-accent/30 transition-colors cursor-pointer">
        <CardContent className="p-4 min-h-[96px] flex flex-col gap-2">
          <div className="flex items-center gap-3">
            <StockLogo card={card} />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="text-sm font-semibold">{card.symbol}</span>
                <Badge variant="outline" className="text-[10px] px-1.5 py-0 font-normal capitalize shrink-0">
                  {card.asset_type}
                </Badge>
                {card.owned && (
                  <Badge className="text-[10px] px-1.5 py-0 font-medium bg-amber-500 text-white hover:bg-amber-600 shrink-0">
                    Owned
                  </Badge>
                )}
              </div>
              <p className="text-xs text-muted-foreground truncate">{card.name}</p>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <p className="text-[11px] text-muted-foreground truncate">
              {card.sector || "\u00A0"}
            </p>
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-sm font-medium tabular-nums">
                {card.price != null ? `$${formatPrice(card.price)}` : "—"}
              </span>
              <span
                className={cn(
                  "flex items-center gap-0.5 text-xs tabular-nums",
                  up && "text-emerald-600",
                  down && "text-red-500",
                  !up && !down && "text-muted-foreground",
                )}
              >
                {up && <TrendingUp className="h-3 w-3" />}
                {down && <TrendingDown className="h-3 w-3" />}
                {formatPercent(card.change_percent)}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

function StocksTab() {
  const [universe, setUniverse] = useState<"all" | "owned">("all");
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");

  // Debounce search so we don't thrash the endpoint as the user types.
  useEffect(() => {
    const id = setTimeout(() => setSearch(searchInput.trim()), 250);
    return () => clearTimeout(id);
  }, [searchInput]);

  const { data, isLoading } = useStockUniverse({
    universe,
    search: search || undefined,
  });

  const items = data?.items ?? [];
  const ownedCount = data?.owned_count ?? 0;
  const totalCount = data?.total ?? 0;

  return (
    <div className="space-y-4">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <div className="flex rounded-lg bg-muted p-0.5">
          {(
            [
              { key: "all", label: "All stocks" },
              { key: "owned", label: "My holdings" },
            ] as const
          ).map((opt) => (
            <button
              key={opt.key}
              type="button"
              onClick={() => setUniverse(opt.key)}
              className={cn(
                "px-4 py-1.5 text-sm font-medium rounded-md transition-colors cursor-pointer",
                universe === opt.key
                  ? "bg-background text-foreground shadow-sm ring-1 ring-amber-500/30"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {opt.label}
              {opt.key === "owned" && ownedCount > 0 && (
                <span className="ml-1.5 text-[10px] opacity-70">
                  ({ownedCount})
                </span>
              )}
            </button>
          ))}
        </div>
        <div className="relative md:w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            placeholder="Search ticker or name…"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="pl-8 h-9 text-sm"
          />
        </div>
      </div>

      {isLoading ? (
        <StocksTabSkeleton />
      ) : items.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            {universe === "owned"
              ? "You don't have any holdings yet. Connect a broker to see them here."
              : `No results for "${search}".`}
          </CardContent>
        </Card>
      ) : (
        <>
          <p className="text-[11px] text-muted-foreground">
            Showing {items.length} of {totalCount}
          </p>
          <div className="grid gap-2 auto-rows-fr md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 min-[2200px]:grid-cols-6">
            {items.map((card) => (
              <StockRow key={card.symbol} card={card} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ── Loading skeletons ──────────────────────────────────────────────

function NewsSkeletonRow() {
  return (
    <div className="flex gap-4 py-4 px-4 border-b border-border last:border-0">
      <div className="flex-1 space-y-2 min-w-0">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-5/6" />
        <div className="flex gap-2 pt-1">
          <Skeleton className="h-4 w-16 rounded-full" />
          <Skeleton className="h-4 w-24" />
        </div>
      </div>
    </div>
  );
}

function MarketSummarySkeleton() {
  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center justify-between mb-3">
          <Skeleton className="h-3 w-32" />
          <Skeleton className="h-3 w-24" />
        </div>
        <Card>
          <CardContent className="p-0 divide-y divide-border">
            {Array.from({ length: 6 }).map((_, i) => (
              <NewsSkeletonRow key={i} />
            ))}
          </CardContent>
        </Card>
      </div>

      <Separator />

      <div>
        <div className="flex items-center justify-between mb-3">
          <Skeleton className="h-3 w-28" />
          <Skeleton className="h-3 w-24" />
        </div>
        <div className="grid gap-3 grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Card key={i} className="h-[200px]">
              <CardContent className="p-4 flex flex-col gap-3 h-full">
                <div className="flex items-center gap-2">
                  <Skeleton className="h-5 w-12 rounded-full" />
                  <Skeleton className="h-3 w-16 ml-auto" />
                </div>
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-5/6" />
                <div className="space-y-2 flex-1">
                  <div className="flex gap-2 items-start">
                    <Skeleton className="h-1.5 w-1.5 rounded-full mt-1.5 shrink-0" />
                    <Skeleton className="h-3 w-full" />
                  </div>
                  <div className="flex gap-2 items-start">
                    <Skeleton className="h-1.5 w-1.5 rounded-full mt-1.5 shrink-0" />
                    <Skeleton className="h-3 w-5/6" />
                  </div>
                  <div className="flex gap-2 items-start">
                    <Skeleton className="h-1.5 w-1.5 rounded-full mt-1.5 shrink-0" />
                    <Skeleton className="h-3 w-4/6" />
                  </div>
                </div>
                <Skeleton className="h-3 w-24" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}

function StocksTabSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <div className="flex rounded-lg bg-muted p-0.5 gap-1">
          <Skeleton className="h-8 w-24 rounded-md" />
          <Skeleton className="h-8 w-28 rounded-md" />
        </div>
        <Skeleton className="h-9 w-full md:w-72 rounded-md" />
      </div>
      <div className="grid gap-2 auto-rows-fr md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 min-[2200px]:grid-cols-6">
        {Array.from({ length: 12 }).map((_, i) => (
          <Card key={i} className="h-[96px]">
            <CardContent className="p-4 flex items-center gap-4 h-full">
              <div className="flex-1 space-y-2 min-w-0">
                <div className="flex items-center gap-2">
                  <Skeleton className="h-4 w-12" />
                  <Skeleton className="h-4 w-14 rounded-full" />
                </div>
                <Skeleton className="h-3 w-3/4" />
              </div>
              <div className="text-right space-y-2 shrink-0">
                <Skeleton className="h-4 w-16 ml-auto" />
                <Skeleton className="h-4 w-12 ml-auto rounded-full" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────

export default function MarketsPage() {
  const [activeSection, setActiveSection] = useState<"news" | "stocks">(() => {
    if (typeof window === "undefined") return "stocks";
    return new URLSearchParams(window.location.search).get("tab") === "news"
      ? "news"
      : "stocks";
  });

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (new URLSearchParams(window.location.search).get("tab") === "news") {
      setActiveSection("news");
    }
  }, []);

  const { data: newsData, isLoading: newsLoading } = useMarketNews();
  const {
    data: portfolioNews,
    isLoading: portfolioNewsLoading,
    isError: portfolioNewsError,
    refetch: refetchPortfolioNews,
  } = usePortfolioNews();

  const headlines: MarketHeadline[] = newsData?.summary?.headlines ?? [];
  const updatedAt = newsData?.summary?.updated_at;
  const apiSources: MarketSource[] = newsData?.sources ?? [];

  const liveSources: MarketSource[] = useMemo(() => {
    if (apiSources.length > 0) return apiSources;
    const seen = new Map<string, MarketSource>();
    for (const h of headlines) {
      if (h.source && !seen.has(h.source)) {
        seen.set(h.source, { name: h.source, url: "" });
      }
    }
    return Array.from(seen.values());
  }, [apiSources, headlines]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <h1 className="text-xl font-semibold tracking-tight">Markets</h1>
          <p className="text-sm text-muted-foreground">
            Market news and the investable stock universe.
          </p>
        </div>
        <div className="flex w-full rounded-lg bg-muted p-0.5 sm:w-auto">
          {(["stocks", "news"] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveSection(tab)}
              className={cn(
                "flex-1 px-4 py-1.5 text-sm font-medium rounded-md transition-colors cursor-pointer capitalize sm:flex-none",
                activeSection === tab
                  ? "bg-background text-foreground shadow-sm ring-1 ring-amber-500/30"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {activeSection === "news" && (
        <>
          {newsLoading ? (
            <MarketSummarySkeleton />
          ) : (
            <div className="w-full space-y-6">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
                    Market Summary
                  </h2>
                  {updatedAt && (
                    <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
                      <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />
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
                    <CardContent className="py-10 text-center text-sm text-muted-foreground">
                      Market summary unavailable right now.
                    </CardContent>
                  </Card>
                )}

                {liveSources.length > 0 && (
                  <div className="mt-4 flex flex-wrap items-center gap-2">
                    <span className="text-[11px] text-muted-foreground uppercase tracking-wider">
                      Sources:
                    </span>
                    {liveSources.map((s) => (
                      <a
                        key={s.name}
                        href={s.url || "#"}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-md border border-border text-muted-foreground hover:text-foreground hover:bg-accent/30 transition-colors"
                      >
                        {s.name}
                        {s.url && <ExternalLink className="h-2.5 w-2.5" />}
                      </a>
                    ))}
                  </div>
                )}
              </div>

              <Separator />
              {portfolioNewsLoading ? (
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <Skeleton className="h-3 w-28" />
                    <Skeleton className="h-3 w-24" />
                  </div>
                  <div className="grid gap-3 grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                    {Array.from({ length: 3 }).map((_, i) => (
                      <Card key={i} className="h-[180px]">
                        <CardContent className="p-4 space-y-3">
                          <div className="flex items-center gap-2">
                            <Skeleton className="h-5 w-12 rounded-full" />
                            <Skeleton className="h-3 w-16 ml-auto" />
                          </div>
                          <Skeleton className="h-4 w-full" />
                          <Skeleton className="h-4 w-5/6" />
                          <Skeleton className="h-3 w-full" />
                          <Skeleton className="h-3 w-4/6" />
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              ) : portfolioNewsError ? (
                <div className="py-8 text-center space-y-3">
                  <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
                    Portfolio News
                  </h2>
                  <p className="text-sm text-muted-foreground">
                    Could not load portfolio news.
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => refetchPortfolioNews()}
                  >
                    Retry
                  </Button>
                </div>
              ) : portfolioNews?.articles?.length ? (
                <PortfolioNewsGrid
                  articles={portfolioNews.articles}
                  updatedAt={portfolioNews.updated_at}
                />
              ) : (
                <div className="py-8 text-center">
                  <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground mb-2">
                    Portfolio News
                  </h2>
                  <p className="text-sm text-muted-foreground">
                    No portfolio news for your holdings right now. Check back later.
                  </p>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {activeSection === "stocks" && <StocksTab />}
    </div>
  );
}
