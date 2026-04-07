"use client";
/**
 * Desktop sidebar: primary nav, optional collapse, and a “Coming soon” section.
 *
 * `ICON_MAP` uses string keys; `"Link"` maps to Lucide’s `LinkIcon` because the
 * icon name collides with Next’s `Link`. Active state treats a path as active if
 * it equals the href or is a child (`pathname.startsWith(href + "/")`). When
 * collapsed, primary and placeholder rows wrap in tooltips for discoverability.
 * `FUTURE_NAV_ITEMS` are non-navigating placeholders (`href: "#"`).
 *
 * Added: 2026-04-03
 */
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Link as LinkIcon,
  TrendingUp,
  ArrowLeftRight,
  PieChart,
  Settings,
  Bot,
  Activity,
  Bell,
  FlaskConical,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { APP_NAME } from "@/lib/constants";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useState } from "react";

const ICON_MAP: Record<string, React.ElementType> = {
  LayoutDashboard,
  Link: LinkIcon,
  TrendingUp,
  ArrowLeftRight,
  PieChart,
  Settings,
  Bot,
  Activity,
  Bell,
  FlaskConical,
};

const NAV_ITEMS = [
  { label: "Dashboard", href: "/dashboard", icon: "LayoutDashboard" },
  { label: "Brokers", href: "/brokers", icon: "Link" },
  { label: "Positions", href: "/positions", icon: "TrendingUp" },
  { label: "Transactions", href: "/transactions", icon: "ArrowLeftRight" },
  { label: "Summary", href: "/summary", icon: "PieChart" },
  { label: "Settings", href: "/settings", icon: "Settings" },
];

const FUTURE_NAV_ITEMS = [
  { label: "AI Assistant", href: "#", icon: "Bot" },
  { label: "Health Score", href: "#", icon: "Activity" },
  { label: "Alerts", href: "#", icon: "Bell" },
  { label: "Scenarios", href: "#", icon: "FlaskConical" },
];

export function SidebarNav() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={cn(
        "hidden md:flex flex-col border-r border-border bg-sidebar h-screen sticky top-0 transition-all duration-200",
        collapsed ? "w-16" : "w-60"
      )}
    >
      <Link href="/dashboard" className="flex items-center gap-2 px-4 h-14 border-b border-border shrink-0 cursor-pointer hover:bg-accent/50 transition-colors">
        <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center shrink-0">
          <TrendingUp className="h-4 w-4 text-primary-foreground" />
        </div>
        {!collapsed && (
          <span className="font-semibold text-sm tracking-tight truncate">
            {APP_NAME}
          </span>
        )}
      </Link>

      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-1">
        {NAV_ITEMS.map((item) => {
          const Icon = ICON_MAP[item.icon];
          // Require `href + "/"` for prefixes so `/broker` does not activate for `/brokers`.
          const isActive = pathname === item.href || pathname.startsWith(item.href + "/");

          const link = (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                isActive
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {!collapsed && <span className="truncate">{item.label}</span>}
            </Link>
          );

          if (collapsed) {
            return (
              <Tooltip key={item.href}>
                <TooltipTrigger>{link}</TooltipTrigger>
                <TooltipContent side="right">{item.label}</TooltipContent>
              </Tooltip>
            );
          }
          return link;
        })}

        <Separator className="my-3" />

        {!collapsed && (
          <p className="px-3 text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">
            Coming soon
          </p>
        )}
        {FUTURE_NAV_ITEMS.map((item) => {
          const Icon = ICON_MAP[item.icon];
          const el = (
            <div
              key={item.label}
              className="flex items-center gap-3 px-3 py-2 rounded-md text-sm text-muted-foreground/50 cursor-not-allowed"
            >
              <Icon className="h-4 w-4 shrink-0" />
              {!collapsed && <span className="truncate">{item.label}</span>}
            </div>
          );
          if (collapsed) {
            return (
              <Tooltip key={item.label}>
                <TooltipTrigger>{el}</TooltipTrigger>
                <TooltipContent side="right">{item.label} (coming soon)</TooltipContent>
              </Tooltip>
            );
          }
          return el;
        })}
      </nav>

      <div className="border-t border-border p-2 shrink-0">
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-center"
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </Button>
      </div>
    </aside>
  );
}
