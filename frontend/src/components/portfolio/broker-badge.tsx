import { Badge } from "@/components/ui/badge";
import { BROKER_LABELS, STATUS_COLORS } from "@/lib/constants";
import { cn } from "@/lib/utils";

interface BrokerBadgeProps {
  brokerType: string;
  className?: string;
}

interface StatusBadgeProps {
  status: string;
  className?: string;
}

export function BrokerBadge({ brokerType, className }: BrokerBadgeProps) {
  return (
    <Badge variant="outline" className={cn("text-xs font-medium capitalize", className)}>
      {BROKER_LABELS[brokerType] || brokerType}
    </Badge>
  );
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <Badge
      variant="secondary"
      className={cn(
        "text-xs font-medium capitalize",
        STATUS_COLORS[status] || "",
        className
      )}
    >
      <span
        className={cn(
          "inline-block h-1.5 w-1.5 rounded-full mr-1.5",
          status === "active" || status === "connected" || status === "healthy" ? "bg-emerald-500" : "",
          status === "pending" || status === "degraded" ? "bg-amber-500" : "",
          status === "error" || status === "expired" || status === "unhealthy" ? "bg-red-500" : "",
          status === "disconnected" ? "bg-zinc-400" : ""
        )}
      />
      {status}
    </Badge>
  );
}
