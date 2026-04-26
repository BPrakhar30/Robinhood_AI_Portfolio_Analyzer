"use client";
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
  Newspaper,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { APP_NAME } from "@/lib/constants";

const NAV_ITEMS = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Brokers", href: "/brokers", icon: LinkIcon },
  { label: "Positions", href: "/positions", icon: TrendingUp },
  { label: "Allocation", href: "/allocation", icon: PieChart },
  { label: "Transactions", href: "/transactions", icon: ArrowLeftRight },
  { label: "AI Assistant", href: "/assistant", icon: Bot },
  { label: "Markets", href: "/markets", icon: Newspaper },
  { label: "Summary", href: "/summary", icon: PieChart },
  { label: "Settings", href: "/settings", icon: Settings },
];

export function MobileSidebar() {
  const pathname = usePathname();

  return (
    <div className="flex flex-col h-full bg-sidebar">
      <Link href="/dashboard" className="flex items-center gap-2 px-4 h-14 border-b border-border cursor-pointer hover:bg-accent/50 transition-colors">
        <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
          <TrendingUp className="h-4 w-4 text-primary-foreground" />
        </div>
        <span className="font-semibold text-sm">{APP_NAME}</span>
      </Link>
      <nav className="flex-1 py-3 px-2 space-y-1">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "relative flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors",
                isActive
                  ? "bg-amber-500/10 text-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
              )}
            >
              {isActive && (
                <span className="absolute left-0 top-2 bottom-2 w-0.5 rounded-r bg-amber-500" />
              )}
              <item.icon
                className={cn(
                  "h-4 w-4",
                  isActive && "text-amber-600 dark:text-amber-400",
                )}
              />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
