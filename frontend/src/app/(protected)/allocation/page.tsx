"use client";

import { PieChart } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { useAllocation } from "@/features/brokers/hooks";
import { AllocationSection } from "@/components/portfolio/allocation-card";
import { formatCurrency } from "@/components/portfolio/currency-text";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";

function AllocationSkeleton() {
  return (
    <div className="space-y-10">
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="space-y-6">
          <Skeleton className="h-6 w-40" />
          <div className="flex flex-col-reverse md:flex-row gap-8">
            <div className="flex-1 space-y-2">
              {Array.from({ length: 5 }).map((_, j) => (
                <Skeleton key={j} className="h-10 w-full rounded-lg" />
              ))}
            </div>
            <div className="w-full md:w-56 lg:w-64 shrink-0">
              <Skeleton className="h-56 lg:h-64 w-full rounded-full mx-auto aspect-square max-w-56 lg:max-w-64" />
            </div>
          </div>
          {i < 2 && <Separator />}
        </div>
      ))}
    </div>
  );
}

export default function AllocationPage() {
  const { data, isLoading, error, refetch } = useAllocation();

  if (error) {
    return (
      <div>
        <PageHeader title="Allocation" />
        <ErrorState
          message="Failed to load allocation data."
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  const sections = data
    ? [
        { title: "Sector Allocation", items: data.by_sector },
        { title: "Asset Class", items: data.by_asset_class },
        { title: "Geography", items: data.by_geography },
        { title: "Market Cap", items: data.by_market_cap },
        { title: "Risk Profile", items: data.by_risk_level },
      ]
    : [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Portfolio Allocation"
        description="Breakdown of your portfolio by sector, asset class, geography, market cap, and risk level"
      />

      {isLoading ? (
        <AllocationSkeleton />
      ) : !data || data.total_value === 0 ? (
        <EmptyState
          icon={PieChart}
          title="No allocation data"
          description="Connect a broker or import a CSV to see your portfolio allocation breakdown."
          actionLabel="Connect Broker"
          actionHref="/brokers"
        />
      ) : (
        <>
          <div className="rounded-lg border bg-card px-4 py-3 text-sm text-muted-foreground">
            Total portfolio value:{" "}
            <span className="font-semibold text-foreground">
              {formatCurrency(data.total_value)}
            </span>
          </div>

          <div className="space-y-10">
            {sections.map((section, idx) => (
              <div key={section.title}>
                <AllocationSection
                  title={section.title}
                  data={section.items}
                />
                {idx < sections.length - 1 && <Separator className="mt-10" />}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
