"use client";

import { useParams, useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  ArrowLeft,
  Building2,
  Calendar,
  ExternalLink,
  Loader2,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import {
  useStockCandles,
  useStockDetail,
} from "@/features/stocks/hooks";
import type {
  CandleRange,
  EarningsQuarter,
  StockDetailResponse,
  StockKeyStats,
  StockNewsItem,
  StockPositionSummary,
  StockProfile,
} from "@/features/stocks/types";

// ── Formatters ────────────────────────────────────────────────────

function fmtPrice(n: number | null | undefined, digits = 2): string {
  if (n == null || Number.isNaN(n)) return "—";
  return n.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function fmtPercent(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}%`;
}

function fmtCompact(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—";
  const abs = Math.abs(n);
  if (abs >= 1e12) return `${(n / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `${(n / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${(n / 1e6).toFixed(2)}M`;
  if (abs >= 1e3) return `${(n / 1e3).toFixed(2)}K`;
  return `${n.toLocaleString("en-US")}`;
}

function fmtInt(n: number | null | undefined): string {
  if (n == null) return "—";
  return n.toLocaleString("en-US");
}

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

// ── Chart ────────────────────────────────────────────────────────

const RANGES: CandleRange[] = ["1D", "1W", "1M", "3M", "YTD", "1Y", "5Y", "MAX"];

function PriceChart({ symbol }: { symbol: string }) {
  const [range, setRange] = useState<CandleRange>("1M");
  const { data, isLoading } = useStockCandles(symbol, range);

  const chartData = useMemo(() => {
    return (data?.points ?? []).map((p) => ({
      t: p.t,
      price: p.c,
    }));
  }, [data]);

  const change = data?.change ?? null;
  const changePct = data?.change_percent ?? null;
  const up = (change ?? 0) >= 0;
  const stroke = up ? "hsl(142, 72%, 42%)" : "hsl(0, 84%, 55%)";
  const fill = up ? "hsl(142, 72%, 42%)" : "hsl(0, 84%, 55%)";

  const tickFormatter = (v: string) => {
    try {
      const d = new Date(v);
      if (range === "1D") {
        return d.toLocaleTimeString("en-US", {
          hour: "numeric",
          minute: "2-digit",
        });
      }
      if (range === "1W" || range === "1M" || range === "3M") {
        return d.toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
        });
      }
      return d.toLocaleDateString("en-US", { month: "short", year: "2-digit" });
    } catch {
      return "";
    }
  };

  return (
    <Card>
      <CardContent className="p-4 space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-wider">
              {range} change
            </p>
            <div
              className={cn(
                "flex items-baseline gap-2 text-lg font-semibold tabular-nums",
                up ? "text-emerald-600" : "text-red-500",
              )}
            >
              <span>
                {change != null ? (change >= 0 ? "+" : "") : ""}
                {change != null ? `$${fmtPrice(Math.abs(change))}` : "—"}
              </span>
              <span className="text-sm">{fmtPercent(changePct)}</span>
            </div>
          </div>
          <div className="flex flex-wrap gap-1 sm:justify-end">
            {RANGES.map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => setRange(r)}
                className={cn(
                  "px-2.5 py-1 text-xs rounded-md font-medium transition-colors cursor-pointer",
                  range === r
                    ? "bg-amber-500/15 text-amber-700 dark:text-amber-300 ring-1 ring-amber-500/40"
                    : "text-muted-foreground hover:bg-accent",
                )}
              >
                {r}
              </button>
            ))}
          </div>
        </div>

        <div className="h-56 min-w-0 sm:h-64 lg:h-72">
          {isLoading ? (
            <div className="h-full flex items-center justify-center">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : chartData.length === 0 ? (
            <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
              No price data available.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
              <AreaChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="gradient-price" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={fill} stopOpacity={0.35} />
                    <stop offset="100%" stopColor={fill} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis
                  dataKey="t"
                  tickFormatter={tickFormatter}
                  tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                  axisLine={false}
                  tickLine={false}
                  minTickGap={28}
                />
                <YAxis
                  domain={["dataMin", "dataMax"]}
                  tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v) => `$${Math.round(v)}`}
                  width={50}
                />
                <Tooltip
                  contentStyle={{
                    background: "hsl(var(--background))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                  labelFormatter={(v) => new Date(String(v)).toLocaleString("en-US")}
                  formatter={(v) => [`$${fmtPrice(Number(v))}`, "Price"]}
                />
                <Area
                  type="monotone"
                  dataKey="price"
                  stroke={stroke}
                  strokeWidth={2}
                  fill="url(#gradient-price)"
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Position card ─────────────────────────────────────────────────

function PositionCard({ pos }: { pos: StockPositionSummary }) {
  if (!pos.owned) {
    return null;
  }
  const up = (pos.total_return ?? 0) >= 0;
  return (
    <Card>
      <CardContent className="p-4 space-y-3">
        <p className="text-xs uppercase tracking-wider text-muted-foreground">
          Your position
        </p>
        <div className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
          <Stat label="Shares" value={pos.shares.toLocaleString("en-US")} />
          <Stat
            label="Market value"
            value={`$${fmtPrice(pos.market_value)}`}
          />
          <Stat
            label="Avg cost"
            value={pos.average_cost != null ? `$${fmtPrice(pos.average_cost)}` : "—"}
          />
          <Stat
            label="Invested"
            value={`$${fmtPrice(pos.total_invested)}`}
          />
          <Stat
            label="Today&apos;s return"
            value={
              <span className={up ? "text-emerald-600" : "text-red-500"}>
                {pos.todays_return != null
                  ? `${pos.todays_return >= 0 ? "+" : ""}$${fmtPrice(Math.abs(pos.todays_return))}`
                  : "—"}{" "}
                ({fmtPercent(pos.todays_return_percent)})
              </span>
            }
          />
          <Stat
            label="Total return"
            value={
              <span className={up ? "text-emerald-600" : "text-red-500"}>
                {pos.total_return != null
                  ? `${pos.total_return >= 0 ? "+" : ""}$${fmtPrice(Math.abs(pos.total_return))}`
                  : "—"}{" "}
                ({fmtPercent(pos.total_return_percent)})
              </span>
            }
          />
          <Stat
            label="Portfolio weight"
            value={fmtPercent(pos.portfolio_weight_percent)}
          />
        </div>
      </CardContent>
    </Card>
  );
}

function Stat({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div>
      <p className="text-[11px] text-muted-foreground uppercase tracking-wider">
        {label}
      </p>
      <p className="text-sm font-medium tabular-nums">{value}</p>
    </div>
  );
}

// ── About ─────────────────────────────────────────────────────────

function businessSummary(profile: StockProfile): string | null {
  const raw = profile.description?.trim();
  if (!raw) {
    if (profile.industry && profile.sector) {
      return `${profile.name} operates in the ${profile.industry} industry within the ${profile.sector} sector.`;
    }
    const focus = profile.industry || profile.sector;
    return focus ? `${profile.name} operates in ${focus}.` : null;
  }
  const sentences = raw
    .replace(/\s+/g, " ")
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter(Boolean);
  return (sentences.slice(0, 2).join(" ") || raw);
}

function AboutCard({ profile }: { profile: StockProfile }) {
  const summary = businessSummary(profile);
  const rows: { label: string; value: string | number | null | undefined }[] = [
    { label: "CEO", value: profile.ceo },
    { label: "Employees", value: fmtInt(profile.employees) },
    { label: "Headquarters", value: profile.headquarters },
    { label: "Founded", value: profile.founded ?? null },
    { label: "IPO", value: fmtDate(profile.ipo_date) },
    { label: "Exchange", value: profile.exchange },
    { label: "Industry", value: profile.industry },
    { label: "Sector", value: profile.sector },
  ].filter((r) => r.value != null && r.value !== "" && r.value !== "—");

  return (
    <Card>
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center gap-2">
          <Building2 className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-sm font-semibold">About</h3>
        </div>
        {rows.length > 0 && (
          <div className="grid grid-cols-2 gap-x-4 gap-y-3">
            {rows.map((r) => (
              <div key={r.label}>
                <p className="text-[11px] text-muted-foreground uppercase tracking-wider">
                  {r.label}
                </p>
                <p className="text-sm">{String(r.value)}</p>
              </div>
            ))}
          </div>
        )}
        {summary && (
          <p className="text-sm text-muted-foreground leading-relaxed line-clamp-2">
            {summary}
          </p>
        )}
        {profile.website && (
          <a
            href={profile.website}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400 hover:underline"
          >
            Visit website
            <ExternalLink className="h-3 w-3" />
          </a>
        )}
      </CardContent>
    </Card>
  );
}

// ── Key stats ─────────────────────────────────────────────────────

function KeyStatsCard({ stats }: { stats: StockKeyStats }) {
  const items: { label: string; value: string }[] = [
    { label: "Market cap", value: stats.market_cap ? `$${fmtCompact(stats.market_cap)}` : "—" },
    { label: "P/E (TTM)", value: fmtPrice(stats.pe_ratio) },
    { label: "Forward P/E", value: fmtPrice(stats.forward_pe) },
    { label: "EPS (TTM)", value: stats.eps_ttm != null ? `$${fmtPrice(stats.eps_ttm)}` : "—" },
    { label: "Beta", value: fmtPrice(stats.beta) },
    {
      label: "Dividend yield",
      value:
        stats.dividend_yield != null
          ? `${(stats.dividend_yield * 100).toFixed(2)}%`
          : "—",
    },
    {
      label: "52-wk high",
      value: stats.fifty_two_week_high != null ? `$${fmtPrice(stats.fifty_two_week_high)}` : "—",
    },
    {
      label: "52-wk low",
      value: stats.fifty_two_week_low != null ? `$${fmtPrice(stats.fifty_two_week_low)}` : "—",
    },
    { label: "Open", value: stats.open_price != null ? `$${fmtPrice(stats.open_price)}` : "—" },
    { label: "Day high", value: stats.day_high != null ? `$${fmtPrice(stats.day_high)}` : "—" },
    { label: "Day low", value: stats.day_low != null ? `$${fmtPrice(stats.day_low)}` : "—" },
    { label: "Volume", value: fmtCompact(stats.volume) },
    { label: "Avg volume", value: fmtCompact(stats.average_volume) },
    {
      label: "Shares outstanding",
      value: fmtCompact(stats.shares_outstanding),
    },
  ];

  return (
    <Card>
      <CardContent className="p-4 space-y-3">
        <h3 className="text-sm font-semibold">Key statistics</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-x-4 gap-y-3">
          {items.map((it) => (
            <div key={it.label}>
              <p className="text-[11px] text-muted-foreground uppercase tracking-wider">
                {it.label}
              </p>
              <p className="text-sm tabular-nums">{it.value}</p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Earnings card ─────────────────────────────────────────────────

function EarningsCard({
  earnings,
}: {
  earnings: StockDetailResponse["earnings"];
}) {
  const next = earnings.next_event;
  const history = earnings.history ?? [];

  return (
    <Card>
      <CardContent className="p-4 space-y-4">
        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-sm font-semibold">Earnings</h3>
        </div>

        {next ? (
          <div className="rounded-md border border-border p-3 bg-accent/20 space-y-1">
            <p className="text-[11px] uppercase tracking-wider text-muted-foreground">
              Next call
            </p>
            <div className="flex items-center gap-2 text-sm font-medium">
              <span>{fmtDate(next.date)}</span>
              {next.hour && (
                <Badge variant="outline" className="text-[10px]">
                  {next.hour}
                </Badge>
              )}
              {next.quarter && next.year && (
                <Badge variant="outline" className="text-[10px]">
                  Q{next.quarter} {next.year}
                </Badge>
              )}
            </div>
            {next.eps_estimate != null && (
              <p className="text-xs text-muted-foreground">
                EPS estimate: ${fmtPrice(next.eps_estimate)}
              </p>
            )}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">
            No upcoming earnings event scheduled.
          </p>
        )}

        {history.length > 0 && (
          <div>
            <p className="text-[11px] uppercase tracking-wider text-muted-foreground mb-2">
              Last {history.length} quarters
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-[11px] uppercase tracking-wider text-muted-foreground">
                    <th className="text-left py-2 pr-2 font-medium">Period</th>
                    <th className="text-right py-2 px-2 font-medium">EPS Est</th>
                    <th className="text-right py-2 px-2 font-medium">EPS Actual</th>
                    <th className="text-right py-2 pl-2 font-medium">Surprise</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {history.map((q: EarningsQuarter, i) => (
                    <tr key={i}>
                      <td className="py-2 pr-2">
                        {q.quarter && q.year ? `Q${q.quarter} ${q.year}` : fmtDate(q.date)}
                      </td>
                      <td className="py-2 px-2 text-right tabular-nums">
                        {q.eps_estimate != null ? `$${fmtPrice(q.eps_estimate)}` : "—"}
                      </td>
                      <td className="py-2 px-2 text-right tabular-nums">
                        {q.eps_actual != null ? `$${fmtPrice(q.eps_actual)}` : "—"}
                      </td>
                      <td
                        className={cn(
                          "py-2 pl-2 text-right tabular-nums font-medium",
                          (q.surprise_percent ?? 0) > 0 && "text-emerald-600",
                          (q.surprise_percent ?? 0) < 0 && "text-red-500",
                        )}
                      >
                        {(q.surprise_percent ?? 0) > 0 && "+"}
                        {q.surprise_percent != null
                          ? `${q.surprise_percent.toFixed(2)}%`
                          : q.reported
                          ? "—"
                          : "Not reported"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── News ──────────────────────────────────────────────────────────

function NewsCard({ news, symbol }: { news: StockNewsItem[]; symbol: string }) {
  return (
    <Card>
      <CardContent className="p-4 space-y-3">
        <h3 className="text-sm font-semibold">News about {symbol}</h3>
        {news.length === 0 ? (
          <p className="text-xs text-muted-foreground">
            No recent news available for this symbol.
          </p>
        ) : (
          <div className="divide-y divide-border">
            {news.map((a) => (
              <a
                key={a.url}
                href={a.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block py-3 hover:bg-accent/20 -mx-4 px-4 transition-colors"
              >
                <div className="flex items-center gap-2 text-[11px] text-muted-foreground mb-1">
                  <span>{a.time_ago}</span>
                </div>
                <p className="text-sm font-medium leading-snug">{a.headline}</p>
                {(a.ai_summary || a.summary) && (
                  <p className="text-xs text-muted-foreground line-clamp-2 mt-1">
                    {a.ai_summary?.trim() || a.summary}
                  </p>
                )}
              </a>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Header ────────────────────────────────────────────────────────

function DetailHeader({ data }: { data: StockDetailResponse }) {
  const { profile, quote } = data;
  const price = quote.price;
  const change = quote.change;
  const changePct = quote.change_percent;
  const up = (change ?? 0) > 0;
  const down = (change ?? 0) < 0;

  return (
    <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
      <div className="flex items-center gap-4">
        {profile.logo ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={profile.logo}
            alt={`${profile.name} logo`}
            className="h-12 w-12 rounded-md border border-border object-contain bg-white"
          />
        ) : (
          <div className="h-12 w-12 rounded-md border border-border bg-muted flex items-center justify-center text-xs font-semibold">
            {profile.symbol.slice(0, 3)}
          </div>
        )}
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold tracking-tight">
              {profile.name}
            </h1>
            <Badge variant="outline" className="text-[10px] capitalize">
              {profile.asset_type}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            {profile.symbol}
            {profile.exchange ? ` · ${profile.exchange}` : ""}
            {profile.sector ? ` · ${profile.sector}` : ""}
          </p>
        </div>
      </div>
      <div className="text-left md:text-right">
        <p className="text-2xl font-semibold tabular-nums">
          {price != null ? `$${fmtPrice(price)}` : "—"}
        </p>
        <div
          className={cn(
            "flex items-center gap-1 text-sm tabular-nums md:justify-end",
            up && "text-emerald-600",
            down && "text-red-500",
            !up && !down && "text-muted-foreground",
          )}
        >
          {up && <TrendingUp className="h-3.5 w-3.5" />}
          {down && <TrendingDown className="h-3.5 w-3.5" />}
          <span>
            {change != null ? `${change >= 0 ? "+" : ""}$${fmtPrice(Math.abs(change))}` : "—"}
          </span>
          <span>({fmtPercent(changePct)})</span>
        </div>
      </div>
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────

export default function StockDetailPage() {
  const params = useParams();
  const router = useRouter();
  const rawSymbol = Array.isArray(params.symbol) ? params.symbol[0] : params.symbol;
  const symbol = (rawSymbol ?? "").toUpperCase();

  const { data, isLoading, isError, error } = useStockDetail(symbol);
  const isCrypto = data
    ? data.profile.asset_type === "crypto" || data.position.asset_type === "crypto"
    : false;

  if (!symbol) {
    return null;
  }

  return (
    <div className="space-y-6">
      <Button
        variant="ghost"
        size="sm"
        className="gap-1 -ml-2 cursor-pointer"
        onClick={() => router.back()}
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back
      </Button>

      {isLoading ? (
        <div className="flex items-center justify-center py-24">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : isError ? (
        <Card>
          <CardContent className="py-10 text-center space-y-2">
            <p className="text-sm font-medium">Unable to load {symbol}.</p>
            <p className="text-xs text-muted-foreground">
              {error instanceof Error && error.message
                ? error.message
                : "Try again in a moment."}
            </p>
          </CardContent>
        </Card>
      ) : data ? (
        <>
          <DetailHeader data={data} />
          <Separator />

          <div
            className={cn(
              "grid gap-4",
              data.position.owned && "lg:grid-cols-[2fr_1fr]",
            )}
          >
            <PriceChart symbol={symbol} />
            {data.position.owned && <PositionCard pos={data.position} />}
          </div>

          <div className={cn("grid gap-4", !isCrypto && "lg:grid-cols-2")}>
            {!isCrypto && <AboutCard profile={data.profile} />}
            <KeyStatsCard stats={data.key_stats} />
          </div>

          {!isCrypto && <EarningsCard earnings={data.earnings} />}

          <NewsCard news={data.news} symbol={symbol} />
        </>
      ) : null}
    </div>
  );
}
