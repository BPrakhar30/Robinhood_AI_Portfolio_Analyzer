"use client";

import {
  Activity,
  ShieldAlert,
  TrendingDown,
  Layers,
  BarChart3,
  DollarSign,
  AlertTriangle,
  Lightbulb,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { PageHeader } from "@/components/layout/page-header";
import { useHealthScore } from "@/features/portfolio-health/hooks";
import { cn } from "@/lib/utils";
import type { SubScoreDetail } from "@/lib/api/types";

const SUB_SCORE_META: Record<string, { icon: React.ElementType; color: string }> = {
  diversification: { icon: Layers, color: "text-blue-600" },
  concentration: { icon: ShieldAlert, color: "text-amber-600" },
  overlap: { icon: BarChart3, color: "text-purple-600" },
  volatility: { icon: TrendingDown, color: "text-red-600" },
  expenses: { icon: DollarSign, color: "text-emerald-600" },
};

const SUB_SCORE_ORDER = ["diversification", "concentration", "overlap", "volatility", "expenses"];

function scoreColor(score: number) {
  if (score >= 80) return "text-emerald-600 dark:text-emerald-400";
  if (score >= 60) return "text-blue-600 dark:text-blue-400";
  if (score >= 40) return "text-amber-600 dark:text-amber-400";
  return "text-red-600 dark:text-red-400";
}

function ringStroke(score: number) {
  if (score >= 80) return "stroke-emerald-500";
  if (score >= 60) return "stroke-blue-500";
  if (score >= 40) return "stroke-amber-500";
  return "stroke-red-500";
}

function gradeColor(grade: string) {
  switch (grade) {
    case "Excellent": return "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400";
    case "Good": return "bg-blue-500/15 text-blue-700 dark:text-blue-400";
    case "Fair": return "bg-amber-500/15 text-amber-700 dark:text-amber-400";
    default: return "bg-red-500/15 text-red-700 dark:text-red-400";
  }
}

function ScoreRing({ score, size = 160 }: { score: number; size?: number }) {
  const r = (size - 16) / 2;
  const circumference = 2 * Math.PI * r;
  const offset = circumference - (score / 100) * circumference;

  return (
    <svg width={size} height={size} className="transform -rotate-90">
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        className="stroke-muted"
        strokeWidth={10}
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        className={cn("transition-all duration-1000", ringStroke(score))}
        strokeWidth={10}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
      />
    </svg>
  );
}

function SubScoreCard({ keyName, data }: { keyName: string; data: SubScoreDetail }) {
  const meta = SUB_SCORE_META[keyName];
  if (!meta) return null;
  const Icon = meta.icon;

  return (
    <Card>
      <CardContent className="pt-5 pb-4 px-5">
        <div className="flex items-start gap-3">
          <div className={cn("p-2 rounded-lg bg-muted shrink-0", meta.color)}>
            <Icon className="h-4 w-4" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium">{data.label}</span>
              <span className={cn("text-lg font-bold tabular-nums", scoreColor(data.score))}>
                {data.score}
              </span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {data.description}
            </p>
            {/* Mini bar */}
            <div className="mt-2 h-1.5 rounded-full bg-muted overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full transition-all duration-700",
                  data.score >= 80 ? "bg-emerald-500" :
                  data.score >= 60 ? "bg-blue-500" :
                  data.score >= 40 ? "bg-amber-500" : "bg-red-500"
                )}
                style={{ width: `${data.score}%` }}
              />
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function HealthScorePage() {
  const { data, isLoading, error } = useHealthScore();

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Portfolio Health Score"
          description="Composite analysis of your portfolio's diversification, concentration, and risk profile."
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
          title="Portfolio Health Score"
          description="Composite analysis of your portfolio's diversification, concentration, and risk profile."
        />
        <Card>
          <CardContent className="py-12 text-center">
            <Activity className="h-10 w-10 text-muted-foreground/40 mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">
              Unable to calculate health score. Connect a broker to get started.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Portfolio Health Score"
        description="Composite analysis of your portfolio's diversification, concentration, and risk profile."
      />

      {/* Score hero */}
      <Card>
        <CardContent className="py-8">
          <div className="flex flex-col md:flex-row items-center gap-8">
            <div className="relative">
              <ScoreRing score={data.overall_score} />
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className={cn("text-4xl font-bold tabular-nums", scoreColor(data.overall_score))}>
                  {Math.round(data.overall_score)}
                </span>
                <span className="text-xs text-muted-foreground">out of 100</span>
              </div>
            </div>

            <div className="flex-1 text-center md:text-left space-y-3">
              <div className="flex items-center gap-2 justify-center md:justify-start">
                <h2 className="text-xl font-semibold">Overall Health</h2>
                <Badge className={gradeColor(data.grade)}>{data.grade}</Badge>
              </div>

              {data.top_issues.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                    <AlertTriangle className="h-3.5 w-3.5" />
                    What&apos;s affecting your score
                  </p>
                  {data.top_issues.map((issue, i) => (
                    <p key={i} className="text-sm text-muted-foreground">
                      • {issue}
                    </p>
                  ))}
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Sub-scores grid */}
      <div>
        <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-3">
          Score Breakdown
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {SUB_SCORE_ORDER.map((key) => {
            const sub = data.sub_scores[key];
            if (!sub) return null;
            return <SubScoreCard key={key} keyName={key} data={sub} />;
          })}
        </div>
      </div>

      {/* Suggestions */}
      {data.suggestions.length > 0 && (
        <>
          <Separator />
          <div>
            <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <Lightbulb className="h-3.5 w-3.5" />
              How to improve
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {data.suggestions.map((s, i) => (
                <Card key={i}>
                  <CardContent className="py-4 px-5">
                    <p className="text-sm text-muted-foreground leading-relaxed">{s}</p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
