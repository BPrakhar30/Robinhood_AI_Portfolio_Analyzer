"use client";

import {
  Bell,
  ShieldAlert,
  Layers,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/layout/page-header";
import { useRiskAlerts } from "@/features/portfolio-health/hooks";
import { cn } from "@/lib/utils";
import type { RiskAlert } from "@/lib/api/types";

const SEVERITY_CONFIG = {
  high: {
    badge: "bg-red-500/15 text-red-700 dark:text-red-400",
    border: "border-l-red-500",
    icon: AlertTriangle,
    label: "High",
  },
  medium: {
    badge: "bg-amber-500/15 text-amber-700 dark:text-amber-400",
    border: "border-l-amber-500",
    icon: ShieldAlert,
    label: "Medium",
  },
  low: {
    badge: "bg-blue-500/15 text-blue-700 dark:text-blue-400",
    border: "border-l-blue-500",
    icon: Bell,
    label: "Low",
  },
} as const;

const CATEGORY_LABELS: Record<string, string> = {
  sector_overweight: "Sector Overweight",
  concentration: "Concentration",
  etf_overlap: "ETF Overlap",
};

function AlertCard({ alert }: { alert: RiskAlert }) {
  const config = SEVERITY_CONFIG[alert.severity] || SEVERITY_CONFIG.low;
  const Icon = config.icon;

  return (
    <Card className={cn("border-l-4", config.border)}>
      <CardContent className="py-4 px-5">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-muted shrink-0 mt-0.5">
            <Icon className="h-4 w-4" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span className="text-sm font-medium">{alert.title}</span>
              <Badge className={cn("text-[10px] px-1.5 py-0", config.badge)}>
                {config.label}
              </Badge>
              <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                {CATEGORY_LABELS[alert.category] || alert.category}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed mb-2">
              {alert.description}
            </p>
            <div className="flex items-center gap-4 text-[11px] text-muted-foreground">
              <span>
                <span className="font-medium text-foreground">{alert.metric}</span>
                {" "}{alert.threshold}
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function AlertsPage() {
  const { data, isLoading, error } = useRiskAlerts();

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Risk Alerts"
          description="Automated detection of concentration risks, sector overweights, and ETF overlap."
        />
        <div className="flex items-center justify-center py-20">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Risk Alerts"
          description="Automated detection of concentration risks, sector overweights, and ETF overlap."
        />
        <Card>
          <CardContent className="py-12 text-center">
            <Bell className="h-10 w-10 text-muted-foreground/40 mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">
              Unable to load alerts. Connect a broker to get started.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const { alerts, summary } = data;
  const total = summary.high + summary.medium + summary.low;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Risk Alerts"
        description="Automated detection of concentration risks, sector overweights, and ETF overlap."
      />

      {/* Summary badges */}
      <div className="flex items-center gap-3 flex-wrap">
        <Badge className={cn("gap-1", SEVERITY_CONFIG.high.badge)}>
          <AlertTriangle className="h-3 w-3" />
          {summary.high} High
        </Badge>
        <Badge className={cn("gap-1", SEVERITY_CONFIG.medium.badge)}>
          <ShieldAlert className="h-3 w-3" />
          {summary.medium} Medium
        </Badge>
        <Badge className={cn("gap-1", SEVERITY_CONFIG.low.badge)}>
          <Bell className="h-3 w-3" />
          {summary.low} Low
        </Badge>
      </div>

      {/* Alert list */}
      {total === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <CheckCircle2 className="h-10 w-10 text-emerald-500/60 mx-auto mb-3" />
            <p className="text-sm font-medium">No risk flags detected</p>
            <p className="text-xs text-muted-foreground mt-1">
              Your portfolio looks well-balanced. We&apos;ll alert you if anything changes.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert) => (
            <AlertCard key={alert.id} alert={alert} />
          ))}
        </div>
      )}
    </div>
  );
}
