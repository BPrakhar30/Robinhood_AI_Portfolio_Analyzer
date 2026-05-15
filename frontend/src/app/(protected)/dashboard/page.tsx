"use client";
import Link from "next/link";
import {
  Link as LinkIcon,
  TrendingUp,
  DollarSign,
  BarChart3,
  Upload,
  ArrowRight,
  Shield,
  Activity,
  AlertTriangle,
  ShieldAlert,
  Bell,
  Gauge,
  Newspaper,
  ThumbsUp,
  Zap,
} from "lucide-react";
import { useAuthStore } from "@/features/auth/store";
import { useConnections, usePositions, useSummary } from "@/features/brokers/hooks";
import { useHealth } from "@/features/system/hooks";
import { useHealthScore, useRiskAlerts } from "@/features/portfolio-health/hooks";
import { usePortfolioNews } from "@/features/stocks/hooks";
import { useMacroAlerts } from "@/features/macro/hooks";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { PageHeader } from "@/components/layout/page-header";
import { StatCard } from "@/components/feedback/stat-card";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { PageSkeleton } from "@/components/feedback/loading-skeleton";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { buttonVariants } from "@/components/ui/button";
import { StatusBadge, BrokerBadge } from "@/components/portfolio/broker-badge";
import { CurrencyText, formatCurrency } from "@/components/portfolio/currency-text";
import { GainLossDisplay } from "@/components/portfolio/gain-loss-display";
import { TimestampText } from "@/components/portfolio/timestamp-text";

const ENABLE_PLAID = process.env.NEXT_PUBLIC_ENABLE_PLAID === "true";

export default function DashboardPage() {
  const { user } = useAuthStore();
  const { data: connections, isLoading: connLoading, error: connError } = useConnections();
  const { data: positions, isLoading: posLoading } = usePositions();
  const { data: summary, isLoading: sumLoading } = useSummary();
  const { data: health } = useHealth();
  const { data: healthScore } = useHealthScore();
  const { data: riskAlerts } = useRiskAlerts();

  const isLoading = connLoading || posLoading || sumLoading;
  const hasConnections = !!connections?.length;
  const { data: portfolioNews, isLoading: portfolioNewsLoading } = usePortfolioNews({
    enabled: hasConnections,
  });
  const { data: macroAlertsData } = useMacroAlerts({ enabled: hasConnections });
  const macroAlerts = macroAlertsData?.alerts ?? [];

  if (isLoading) return <PageSkeleton />;

  const portfolioArticles = portfolioNews?.articles ?? [];
  const portfolioRiskCount = portfolioArticles.filter((a) => a.sentiment === "negative").length;
  const portfolioPositiveCount = portfolioArticles.filter((a) => a.sentiment === "positive").length;
  const portfolioNewsCount = portfolioArticles.length;

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Welcome${user?.full_name ? `, ${user.full_name.split(" ")[0]}` : ""}`}
        description="Your portfolio overview and account connections"
      />

      {/* No connections — onboarding */}
      {!hasConnections && (
        <Card className="border-dashed border-2">
          <CardContent className="py-10 px-6">
            <div className="text-center max-w-lg mx-auto">
              <div className="rounded-full bg-muted p-4 w-fit mx-auto mb-4">
                <LinkIcon className="h-8 w-8 text-muted-foreground" />
              </div>
              <h3 className="text-lg font-semibold mb-2">Connect your first account</h3>
              <p className="text-sm text-muted-foreground mb-6">
                Link your brokerage account to start importing positions and transaction history.
                Choose the method that works best for you.
              </p>
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <Link href="/brokers?connect=robinhood" className={buttonVariants()}>
                  Connect Robinhood
                </Link>
                {ENABLE_PLAID && (
                  <Link href="/brokers?connect=plaid" className={buttonVariants({ variant: "outline" })}>
                    <Shield className="mr-2 h-4 w-4" />
                    Connect via Plaid
                  </Link>
                )}
                <Link href="/brokers?connect=csv" className={buttonVariants({ variant: "outline" })}>
                  <Upload className="mr-2 h-4 w-4" />
                  Import CSV
                </Link>
              </div>
              <p className="text-xs text-muted-foreground mt-4">
                Choose any method above. Robinhood for direct login
                {ENABLE_PLAID ? ", Plaid for automatic account linking," : ""}
                {" "}or CSV for manual import.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Summary stats */}
      {hasConnections && summary && (
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            title="Total Portfolio Value"
            value={formatCurrency(summary.total_value)}
            icon={DollarSign}
          />
          <StatCard
            title="Positions"
            value={summary.positions_count}
            subtitle={`Across ${connections.length} broker${connections.length > 1 ? "s" : ""}`}
            icon={TrendingUp}
          />
          <StatCard
            title="Unrealized Gains"
            value={formatCurrency(summary.total_unrealized_gains)}
            trend={summary.total_unrealized_gains >= 0 ? "up" : "down"}
            icon={BarChart3}
          />
          <StatCard
            title="Cash Balance"
            value={formatCurrency(summary.cash_balance)}
            icon={DollarSign}
          />
        </div>
      )}

      {/* Macro Alert banner — threshold-triggered, only shows when active */}
      {hasConnections && macroAlerts.length > 0 && (
        <Link href="/macro-pulse" className="group block">
          <Card className={cn(
            "border-l-[3px] transition-all hover:shadow-md",
            macroAlerts.some((a) => a.severity === "critical")
              ? "border-l-red-500 bg-red-500/5 hover:border-red-500/80"
              : "border-l-amber-500 bg-amber-500/5 hover:border-amber-500/80",
          )}>
            <CardContent className="py-3 px-4 sm:px-5">
              <div className="flex items-center gap-3">
                <Zap className={cn(
                  "h-5 w-5 shrink-0",
                  macroAlerts.some((a) => a.severity === "critical")
                    ? "text-red-600 dark:text-red-400"
                    : "text-amber-600 dark:text-amber-400",
                )} />
                <div className="flex-1 min-w-0">
                  <p className={cn(
                    "text-sm font-medium",
                    macroAlerts.some((a) => a.severity === "critical")
                      ? "text-red-700 dark:text-red-400"
                      : "text-amber-700 dark:text-amber-400",
                  )}>
                    Macro Alert: {macroAlerts[0].title}
                    {macroAlerts.length > 1 && (
                      <span className="text-xs font-normal ml-2 opacity-75">
                        +{macroAlerts.length - 1} more
                      </span>
                    )}
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                    {macroAlerts[0].message}
                  </p>
                </div>
                <div className="inline-flex shrink-0 items-center gap-1 text-xs font-medium text-amber-700 dark:text-amber-400 group-hover:underline">
                  See Macro Pulse
                  <ArrowRight className="h-3 w-3" />
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>
      )}

      {/* Health Score + Risk Alerts + Portfolio News row */}
      {hasConnections && (healthScore || riskAlerts || portfolioNewsLoading || portfolioNewsCount > 0) && (
        <div className="grid gap-4 grid-cols-1 xl:grid-cols-2 2xl:grid-cols-3">
          {/* Health Score badge */}
          {healthScore && (
            <Link href="/health" className="group block h-full">
              <Card className="h-full cursor-pointer border-border/80 transition-all hover:-translate-y-0.5 hover:border-amber-500/60 hover:bg-amber-50/40 hover:shadow-md dark:hover:bg-amber-950/15">
                <CardContent className="py-5 px-5">
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
                    <div className="relative h-14 w-14 shrink-0">
                      <svg width={56} height={56} className="transform -rotate-90">
                        <circle cx={28} cy={28} r={22} fill="none" className="stroke-muted" strokeWidth={5} />
                        <circle
                          cx={28} cy={28} r={22} fill="none"
                          className={cn(
                            "transition-all",
                            healthScore.overall_score >= 80 ? "stroke-emerald-500" :
                            healthScore.overall_score >= 60 ? "stroke-blue-500" :
                            healthScore.overall_score >= 40 ? "stroke-amber-500" : "stroke-red-500"
                          )}
                          strokeWidth={5}
                          strokeLinecap="round"
                          strokeDasharray={2 * Math.PI * 22}
                          strokeDashoffset={2 * Math.PI * 22 * (1 - healthScore.overall_score / 100)}
                        />
                      </svg>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span className={cn(
                          "text-sm font-bold tabular-nums",
                          healthScore.overall_score >= 80 ? "text-emerald-600" :
                          healthScore.overall_score >= 60 ? "text-blue-600" :
                          healthScore.overall_score >= 40 ? "text-amber-600" : "text-red-600"
                        )}>
                          {Math.round(healthScore.overall_score)}
                        </span>
                      </div>
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium">Health Score</p>
                      <p className="text-xs text-muted-foreground">
                        {healthScore.grade} — {healthScore.top_issues[0]?.split(":")[0] || "Looking good"}
                      </p>
                    </div>
                    <div className="inline-flex shrink-0 items-center gap-1 rounded-full border border-amber-500/40 px-3 py-1 text-xs font-medium text-amber-700 transition-colors group-hover:bg-amber-500 group-hover:text-white dark:text-amber-400 sm:ml-auto">
                      View details
                      <ArrowRight className="h-3 w-3" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          )}

          {/* Risk Alerts widget */}
          {riskAlerts && (
            <Link href="/alerts" className="group block h-full">
              <Card className="h-full cursor-pointer border-border/80 transition-all hover:-translate-y-0.5 hover:border-amber-500/60 hover:bg-amber-50/40 hover:shadow-md dark:hover:bg-amber-950/15">
                <CardContent className="py-5 px-5">
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
                    <div className={cn(
                      "h-14 w-14 rounded-xl flex items-center justify-center shrink-0",
                      riskAlerts.summary.high > 0 ? "bg-red-500/10" :
                      riskAlerts.summary.medium > 0 ? "bg-amber-500/10" : "bg-emerald-500/10"
                    )}>
                      <Activity className={cn(
                        "h-6 w-6",
                        riskAlerts.summary.high > 0 ? "text-red-600" :
                        riskAlerts.summary.medium > 0 ? "text-amber-600" : "text-emerald-600"
                      )} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium">Risk Alerts</p>
                      <div className="flex items-center gap-2 mt-1">
                        {riskAlerts.summary.high > 0 && (
                          <Badge className="bg-red-500/15 text-red-700 dark:text-red-400 text-[10px] px-1.5 py-0 gap-0.5">
                            <AlertTriangle className="h-2.5 w-2.5" />{riskAlerts.summary.high}
                          </Badge>
                        )}
                        {riskAlerts.summary.medium > 0 && (
                          <Badge className="bg-amber-500/15 text-amber-700 dark:text-amber-400 text-[10px] px-1.5 py-0 gap-0.5">
                            <ShieldAlert className="h-2.5 w-2.5" />{riskAlerts.summary.medium}
                          </Badge>
                        )}
                        {riskAlerts.summary.low > 0 && (
                          <Badge className="bg-blue-500/15 text-blue-700 dark:text-blue-400 text-[10px] px-1.5 py-0 gap-0.5">
                            <Bell className="h-2.5 w-2.5" />{riskAlerts.summary.low}
                          </Badge>
                        )}
                        {riskAlerts.alerts.length === 0 && (
                          <span className="text-xs text-emerald-600">No flags detected</span>
                        )}
                      </div>
                    </div>
                    <div className="inline-flex shrink-0 items-center gap-1 rounded-full border border-amber-500/40 px-3 py-1 text-xs font-medium text-amber-700 transition-colors group-hover:bg-amber-500 group-hover:text-white dark:text-amber-400">
                      Open alerts
                      <ArrowRight className="h-3 w-3" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          )}

          {/* Portfolio News widget */}
          <Link href="/markets?tab=news" className="group block h-full">
            <Card className="h-full cursor-pointer border-border/80 transition-all hover:-translate-y-0.5 hover:border-amber-500/60 hover:bg-amber-50/40 hover:shadow-md dark:hover:bg-amber-950/15">
              <CardContent className="py-5 px-5">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
                  <div className="h-14 w-14 rounded-xl flex items-center justify-center shrink-0 bg-amber-500/10">
                    <Newspaper className="h-6 w-6 text-amber-600 dark:text-amber-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">Portfolio News</p>
                    <p className="text-xs text-muted-foreground">
                      Risk and positive updates across your holdings
                    </p>
                    <div className="flex flex-wrap items-center gap-2 mt-2">
                      {portfolioNewsLoading ? (
                        <span className="text-xs text-muted-foreground">Checking latest stories…</span>
                      ) : (
                        <>
                          <Badge className="bg-red-500/15 text-red-700 dark:text-red-400 text-[10px] px-1.5 py-0 gap-0.5">
                            <AlertTriangle className="h-2.5 w-2.5" />
                            Risks {portfolioRiskCount}
                          </Badge>
                          <Badge className="bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 text-[10px] px-1.5 py-0 gap-0.5">
                            <ThumbsUp className="h-2.5 w-2.5" />
                            Positives {portfolioPositiveCount}
                          </Badge>
                          <Badge variant="outline" className="text-[10px] px-1.5 py-0 font-normal">
                            {portfolioNewsCount} total
                          </Badge>
                        </>
                      )}
                    </div>
                  </div>
                  <div className="inline-flex shrink-0 items-center gap-1 rounded-full border border-amber-500/40 px-3 py-1 text-xs font-medium text-amber-700 transition-colors group-hover:bg-amber-500 group-hover:text-white dark:text-amber-400">
                    Open news
                    <ArrowRight className="h-3 w-3" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </Link>
        </div>
      )}

      {/* Connection status + quick actions */}
      {hasConnections && (
        <div className="grid gap-6 xl:grid-cols-2 min-[2200px]:grid-cols-[1.15fr_0.85fr]">
          {/* Connections */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">Broker Connections</CardTitle>
                <Link href="/brokers" className={buttonVariants({ variant: "ghost", size: "sm" })}>
                  Manage <ArrowRight className="ml-1 h-3 w-3" />
                </Link>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {connections.map((conn) => (
                <div
                  key={conn.id}
                  className="flex items-center justify-between p-3 rounded-lg border border-border"
                >
                  <div className="flex items-center gap-3">
                    <BrokerBadge brokerType={conn.broker_type} />
                    <div>
                      <StatusBadge status={conn.status} />
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Last sync: <TimestampText date={conn.last_sync_at} />
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Top positions preview */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">Top Holdings</CardTitle>
                <Link href="/positions" className={buttonVariants({ variant: "ghost", size: "sm" })}>
                  View all <ArrowRight className="ml-1 h-3 w-3" />
                </Link>
              </div>
            </CardHeader>
            <CardContent>
              {positions && positions.length > 0 ? (
                <div className="space-y-2">
                  {positions.slice(0, 5).map((pos) => (
                    <div
                      key={pos.symbol}
                      className="flex items-center justify-between py-2 border-b border-border last:border-0"
                    >
                      <div>
                        <p className="text-sm font-medium">{pos.symbol}</p>
                        <p className="text-xs text-muted-foreground truncate max-w-[160px]">
                          {pos.name}
                        </p>
                      </div>
                      <div className="text-right">
                        <CurrencyText value={pos.market_value} className="text-sm" />
                        <div className="mt-0.5">
                          <GainLossDisplay
                            value={pos.unrealized_gains}
                            invested={pos.total_amount_invested}
                            align="right"
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground py-4 text-center">
                  No positions found yet. Sync your broker to see holdings.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* System status */}
      {health && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">System Status</CardTitle>
          </CardHeader>
          <CardContent>
                <div className="flex flex-col gap-3 text-sm sm:flex-row sm:items-center sm:gap-6">
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">API:</span>
                <StatusBadge status="healthy" />
              </div>
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">Environment:</span>
                <span className="font-mono text-xs">{health.environment}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
