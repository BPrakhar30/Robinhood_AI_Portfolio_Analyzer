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
} from "lucide-react";
import { useAuthStore } from "@/features/auth/store";
import { useConnections, usePositions, useSummary } from "@/features/brokers/hooks";
import { useHealth } from "@/features/system/hooks";
import { useHealthScore, useRiskAlerts } from "@/features/portfolio-health/hooks";
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

export default function DashboardPage() {
  const { user } = useAuthStore();
  const { data: connections, isLoading: connLoading, error: connError } = useConnections();
  const { data: positions, isLoading: posLoading } = usePositions();
  const { data: summary, isLoading: sumLoading } = useSummary();
  const { data: health } = useHealth();
  const { data: healthScore } = useHealthScore();
  const { data: riskAlerts } = useRiskAlerts();

  const isLoading = connLoading || posLoading || sumLoading;

  if (isLoading) return <PageSkeleton />;

  const hasConnections = connections && connections.length > 0;

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
                <Link href="/brokers?connect=plaid" className={buttonVariants({ variant: "outline" })}>
                  <Shield className="mr-2 h-4 w-4" />
                  Connect via Plaid
                </Link>
                <Link href="/brokers?connect=csv" className={buttonVariants({ variant: "outline" })}>
                  <Upload className="mr-2 h-4 w-4" />
                  Import CSV
                </Link>
              </div>
              <p className="text-xs text-muted-foreground mt-4">
                Choose any method above. Robinhood for direct login, Plaid for automatic account linking, or CSV for manual import.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Summary stats */}
      {hasConnections && summary && (
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
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

      {/* Health Score + Risk Alerts row */}
      {hasConnections && (healthScore || riskAlerts) && (
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-2">
          {/* Health Score badge */}
          {healthScore && (
            <Link href="/health">
              <Card className="hover:bg-accent/30 transition-colors cursor-pointer h-full">
                <CardContent className="py-5 px-5">
                  <div className="flex items-center gap-4">
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
                    <div>
                      <p className="text-sm font-medium">Health Score</p>
                      <p className="text-xs text-muted-foreground">
                        {healthScore.grade} — {healthScore.top_issues[0]?.split(":")[0] || "Looking good"}
                      </p>
                    </div>
                    <ArrowRight className="h-4 w-4 text-muted-foreground ml-auto shrink-0" />
                  </div>
                </CardContent>
              </Card>
            </Link>
          )}

          {/* Risk Alerts widget */}
          {riskAlerts && (
            <Link href="/alerts">
              <Card className="hover:bg-accent/30 transition-colors cursor-pointer h-full">
                <CardContent className="py-5 px-5">
                  <div className="flex items-center gap-4">
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
                    <ArrowRight className="h-4 w-4 text-muted-foreground shrink-0" />
                  </div>
                </CardContent>
              </Card>
            </Link>
          )}
        </div>
      )}

      {/* Connection status + quick actions */}
      {hasConnections && (
        <div className="grid gap-6 lg:grid-cols-2">
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
            <div className="flex items-center gap-6 text-sm">
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
