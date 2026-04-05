"use client";
import {
  DollarSign,
  TrendingUp,
  TrendingDown,
  Link as LinkIcon,
  PieChart,
  BarChart3,
} from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { StatCard } from "@/components/feedback/stat-card";
import { ErrorState } from "@/components/feedback/error-state";
import { PageSkeleton } from "@/components/feedback/loading-skeleton";
import { EmptyState } from "@/components/feedback/empty-state";
import { useSummary, useConnections, usePositions } from "@/features/brokers/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatCurrency } from "@/components/portfolio/currency-text";
import { BrokerBadge, StatusBadge } from "@/components/portfolio/broker-badge";
import { TimestampText } from "@/components/portfolio/timestamp-text";

export default function SummaryPage() {
  const { data: summary, isLoading: sumLoading, error: sumError, refetch } = useSummary();
  const { data: connections, isLoading: connLoading } = useConnections();
  const { data: positions, isLoading: posLoading } = usePositions();

  const isLoading = sumLoading || connLoading || posLoading;

  if (isLoading) return <PageSkeleton />;

  if (sumError) {
    return (
      <div>
        <PageHeader title="Summary" />
        <ErrorState message="Failed to load account summary." onRetry={() => refetch()} />
      </div>
    );
  }

  if (!connections || connections.length === 0) {
    return (
      <div>
        <PageHeader title="Summary" />
        <EmptyState
          icon={PieChart}
          title="No data yet"
          description="Connect a broker to see your aggregated account summary."
          actionLabel="Connect Broker"
          actionHref="/brokers"
        />
      </div>
    );
  }

  const assetTypeCounts: Record<string, number> = {};
  positions?.forEach((p) => {
    const type = p.asset_type || "stock";
    assetTypeCounts[type] = (assetTypeCounts[type] || 0) + 1;
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Account Summary"
        description="Aggregated overview across all connected brokers"
      />

      {summary && (
        <>
          <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              title="Total Portfolio Value"
              value={formatCurrency(summary.total_value)}
              icon={DollarSign}
            />
            <StatCard
              title="Total Positions"
              value={summary.positions_count}
              subtitle={`Across ${connections.length} source${connections.length > 1 ? "s" : ""}`}
              icon={TrendingUp}
            />
            <StatCard
              title="Unrealized Gains"
              value={formatCurrency(summary.total_unrealized_gains)}
              trend={summary.total_unrealized_gains >= 0 ? "up" : "down"}
              icon={summary.total_unrealized_gains >= 0 ? TrendingUp : TrendingDown}
            />
            <StatCard
              title="Cash Balance"
              value={formatCurrency(summary.cash_balance)}
              icon={DollarSign}
            />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            {/* Connected brokers */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Connected Sources</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {connections.map((conn) => (
                  <div
                    key={conn.id}
                    className="flex items-center justify-between p-3 rounded-lg border"
                  >
                    <div className="flex items-center gap-3">
                      <BrokerBadge brokerType={conn.broker_type} />
                      <StatusBadge status={conn.status} />
                    </div>
                    <TimestampText date={conn.last_sync_at} className="text-xs" />
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Asset type breakdown */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Asset Breakdown</CardTitle>
              </CardHeader>
              <CardContent>
                {Object.entries(assetTypeCounts).length > 0 ? (
                  <div className="space-y-3">
                    {Object.entries(assetTypeCounts)
                      .sort(([, a], [, b]) => b - a)
                      .map(([type, count]) => (
                        <div key={type} className="flex items-center justify-between">
                          <span className="text-sm capitalize">{type}</span>
                          <div className="flex items-center gap-3">
                            <div className="w-24 h-2 bg-muted rounded-full overflow-hidden">
                              <div
                                className="h-full bg-primary rounded-full"
                                style={{
                                  width: `${(count / (positions?.length || 1)) * 100}%`,
                                }}
                              />
                            </div>
                            <span className="text-sm tabular-nums text-muted-foreground w-8 text-right">
                              {count}
                            </span>
                          </div>
                        </div>
                      ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    No position data available yet.
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
