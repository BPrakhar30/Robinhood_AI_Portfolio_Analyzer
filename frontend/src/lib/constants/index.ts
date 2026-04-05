export const APP_NAME = "RobinhoodAI Copilot";
export const APP_DESCRIPTION = "AI Portfolio Copilot for Robinhood users";

export const NAV_ITEMS = [
  { label: "Dashboard", href: "/dashboard", icon: "LayoutDashboard" },
  { label: "Brokers", href: "/brokers", icon: "Link" },
  { label: "Positions", href: "/positions", icon: "TrendingUp" },
  { label: "Transactions", href: "/transactions", icon: "ArrowLeftRight" },
  { label: "Summary", href: "/summary", icon: "PieChart" },
  { label: "Settings", href: "/settings", icon: "Settings" },
] as const;

export const FUTURE_NAV_ITEMS = [
  { label: "AI Assistant", href: "#", icon: "Bot", disabled: true },
  { label: "Health Score", href: "#", icon: "Activity", disabled: true },
  { label: "Alerts", href: "#", icon: "Bell", disabled: true },
  { label: "Scenarios", href: "#", icon: "FlaskConical", disabled: true },
] as const;

export const BROKER_LABELS: Record<string, string> = {
  robinhood: "Robinhood",
  plaid: "Plaid",
  csv: "CSV Import",
};

export const STATUS_COLORS: Record<string, string> = {
  active: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400",
  connected: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400",
  pending: "bg-amber-500/15 text-amber-700 dark:text-amber-400",
  disconnected: "bg-zinc-500/15 text-zinc-600 dark:text-zinc-400",
  error: "bg-red-500/15 text-red-700 dark:text-red-400",
  expired: "bg-red-500/15 text-red-700 dark:text-red-400",
  healthy: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400",
  degraded: "bg-amber-500/15 text-amber-700 dark:text-amber-400",
  unhealthy: "bg-red-500/15 text-red-700 dark:text-red-400",
};
