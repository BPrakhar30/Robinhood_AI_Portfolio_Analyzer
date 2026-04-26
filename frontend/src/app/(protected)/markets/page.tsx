"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  ChevronDown,
  ExternalLink,
  Loader2,
  Search,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
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

// Bullets we never want to leak into the UI even if the model regresses.
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

// Strips ANY leading combination of bullet glyphs (•, ‣, ◦, ⁃),
// dashes, asterisks, and whitespace — so even nested artefacts like
// "• • text" or "* - text" reduce to clean text. The amber dot in the
// rendered <li> always provides exactly one visible bullet, never two.
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

  // Prefer the LLM's bullet structure when it's there: each line is a bullet.
  let lines = raw.split(/\n+/).map(stripBullet).filter(Boolean);

  // If we didn't get >= 2 lines, fall back to sentence splitting on the
  // collapsed text so we still extract real points from prose summaries.
  if (lines.length < 2) {
    const flat = raw.replace(/\s+/g, " ");
    lines = flat
      .split(/(?<=[.!?])\s+/)
      .map((s) => stripBullet(s))
      .filter(Boolean);
  }

  // Normalize whitespace, drop trailing periods (we re-add the dot via the
  // amber span), and drop filler / duplicates. We DO NOT pad with the
  // headline anymore — duplicate bullets are worse than fewer bullets.
  const seen = new Set<string>();
  const headlineKey = item.headline.trim().toLowerCase();
  const cleaned: string[] = [];

  for (const line of lines) {
    const text = line.replace(/\s+/g, " ").replace(/\.+$/, "").trim();
    const key = text.toLowerCase();
    if (!text || isFiller(text)) continue;
    if (key === headlineKey) continue;
    if (seen.has(key)) continue;
    seen.add(key);
    cleaned.push(text);
    if (cleaned.length === 3) break;
  }

  return cleaned;
}

function PortfolioNewsCard({ item }: { item: StockNewsItem }) {
  const points = summaryPoints(item);
  return (
    <a
      href={item.url}
      target="_blank"
      rel="noopener noreferrer"
      className="group block h-full"
    >
      <Card className="h-full flex flex-col hover:bg-accent/20 hover:border-amber-500/40 transition-colors cursor-pointer">
        <CardContent className="p-4 flex-1 flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
            {item.symbol && (
              <Badge className="text-[10px] px-1.5 py-0 font-medium bg-amber-500/15 text-amber-700 dark:text-amber-300 hover:bg-amber-500/25 border-transparent">
                {item.symbol}
              </Badge>
            )}
            <span className="ml-auto">{item.time_ago}</span>
          </div>
          <h4 className="text-sm font-semibold leading-snug line-clamp-3 group-hover:text-foreground transition-colors">
            {item.headline}
          </h4>
          {points.length > 0 ? (
            <ul className="space-y-1.5 text-xs text-muted-foreground leading-relaxed flex-1">
              {points.map((point, idx) => (
                <li key={idx} className="flex gap-2">
                  <span className="mt-1.5 h-1 w-1 rounded-full bg-amber-500 shrink-0" />
                  <span className="line-clamp-3">{point}</span>
                </li>
              ))}
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
  const visible = showAll ? articles : articles.slice(0, PORTFOLIO_NEWS_INITIAL);
  const hasMore = articles.length > PORTFOLIO_NEWS_INITIAL;

  if (!articles.length) return null;

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-baseline gap-2">
          <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
            Portfolio News
          </h2>
          <span className="text-[11px] text-muted-foreground">
            {articles.length} {articles.length === 1 ? "story" : "stories"} across your holdings
          </span>
        </div>
        {updatedAt && (
          <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />
            Updated {timeAgo(updatedAt)}
          </span>
        )}
      </div>

      <div className="grid gap-3 grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
        {visible.map((a, i) => (
          <PortfolioNewsCard key={`${a.url}-${i}`} item={a} />
        ))}
      </div>

      {hasMore && (
        <div className="mt-4 flex justify-center">
          <button
            type="button"
            onClick={() => setShowAll((v) => !v)}
            className="inline-flex items-center gap-1.5 px-4 py-1.5 text-xs font-medium rounded-md border border-border text-muted-foreground hover:text-foreground hover:border-amber-500/40 hover:bg-amber-500/5 transition-colors cursor-pointer"
          >
            {showAll ? "Show less" : `Show all ${articles.length} stories`}
          </button>
        </div>
      )}
    </div>
  );
}

// ── Stocks tab ─────────────────────────────────────────────────────

function StockRow({ card }: { card: StockCardType }) {
  const up = (card.change_percent ?? 0) > 0;
  const down = (card.change_percent ?? 0) < 0;
  return (
    <Link
      href={`/markets/${encodeURIComponent(card.symbol)}`}
      className="block h-full"
    >
      <Card className="h-full hover:bg-accent/30 transition-colors cursor-pointer">
        <CardContent className="p-4 min-h-[96px] flex items-center gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <p className="text-sm font-semibold">{card.symbol}</p>
              <Badge variant="outline" className="text-[10px] px-1.5 py-0 font-normal capitalize">
                {card.asset_type}
              </Badge>
              {card.owned && (
                <Badge className="text-[10px] px-1.5 py-0 font-medium bg-amber-500 text-white hover:bg-amber-600">
                  Owned
                </Badge>
              )}
            </div>
            <p className="text-xs text-muted-foreground truncate">{card.name}</p>
            <p className="text-[11px] text-muted-foreground mt-0.5 min-h-[1rem]">
              {card.sector || ""}
            </p>
          </div>
          <div className="text-right">
            <p className="text-sm font-medium tabular-nums">
              {card.price != null ? `$${formatPrice(card.price)}` : "—"}
            </p>
            <div
              className={cn(
                "flex items-center justify-end gap-1 text-xs tabular-nums",
                up && "text-emerald-600",
                down && "text-red-500",
                !up && !down && "text-muted-foreground",
              )}
            >
              {up && <TrendingUp className="h-3 w-3" />}
              {down && <TrendingDown className="h-3 w-3" />}
              <span>{formatPercent(card.change_percent)}</span>
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
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
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

// ── Main page ──────────────────────────────────────────────────────

export default function MarketsPage() {
  const [activeSection, setActiveSection] = useState<"news" | "stocks">("stocks");

  const { data: newsData, isLoading: newsLoading } = useMarketNews();
  const { data: portfolioNews, isLoading: portfolioNewsLoading } =
    usePortfolioNews();

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

      {/* News section spreads across the app shell like the other protected
          pages. Individual rows still keep their own padding/readability. */}
      {activeSection === "news" && (
        <>
          {newsLoading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
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

              {/* Portfolio News — grid (not a carousel) so the user can
                  scan many cards at once. Visually distinct from Market
                  Summary above, which is a vertical row list. */}
              {portfolioNewsLoading ? null : portfolioNews?.articles?.length ? (
                <>
                  <Separator />
                  <PortfolioNewsGrid
                    articles={portfolioNews.articles}
                    updatedAt={portfolioNews.updated_at}
                  />
                </>
              ) : null}
            </div>
          )}
        </>
      )}

      {/* Stocks section */}
      {activeSection === "stocks" && <StocksTab />}
    </div>
  );
}
