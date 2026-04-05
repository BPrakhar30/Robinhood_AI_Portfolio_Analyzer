"use client";
import { useState, useMemo } from "react";
import { TrendingUp, Search, ArrowUpDown } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { TableSkeleton } from "@/components/feedback/loading-skeleton";
import { usePositions } from "@/features/brokers/hooks";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { CurrencyText } from "@/components/portfolio/currency-text";
import { GainLossBadge } from "@/components/portfolio/gain-loss-badge";
import { Badge } from "@/components/ui/badge";

type SortKey = "symbol" | "market_value" | "unrealized_gains" | "weight_percent" | "quantity";
type SortDir = "asc" | "desc";

export default function PositionsPage() {
  const { data: positions, isLoading, error, refetch } = usePositions();
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("market_value");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const filtered = useMemo(() => {
    if (!positions) return [];
    let result = positions.filter(
      (p) =>
        p.symbol.toLowerCase().includes(search.toLowerCase()) ||
        p.name.toLowerCase().includes(search.toLowerCase())
    );

    result.sort((a, b) => {
      const aVal = a[sortKey] ?? 0;
      const bVal = b[sortKey] ?? 0;
      if (typeof aVal === "string" && typeof bVal === "string") {
        return sortDir === "asc" ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      }
      return sortDir === "asc"
        ? (aVal as number) - (bVal as number)
        : (bVal as number) - (aVal as number);
    });

    return result;
  }, [positions, search, sortKey, sortDir]);

  if (error) {
    return (
      <div>
        <PageHeader title="Positions" />
        <ErrorState message="Failed to load positions." onRetry={() => refetch()} />
      </div>
    );
  }

  const SortButton = ({ label, field }: { label: string; field: SortKey }) => (
    <Button
      variant="ghost"
      size="sm"
      className="h-auto p-0 font-medium text-xs hover:bg-transparent"
      onClick={() => toggleSort(field)}
    >
      {label}
      <ArrowUpDown className="ml-1 h-3 w-3" />
    </Button>
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Positions"
        description="All holdings across your connected accounts"
      />

      {isLoading ? (
        <TableSkeleton />
      ) : !positions || positions.length === 0 ? (
        <EmptyState
          icon={TrendingUp}
          title="No positions yet"
          description="Connect a broker or import a CSV to see your holdings here."
          actionLabel="Connect Broker"
          actionHref="/brokers"
        />
      ) : (
        <>
          {/* Search bar */}
          <div className="relative max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search by ticker or name..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>

          {/* Table */}
          <Card>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="sticky left-0 bg-background z-10">
                        <SortButton label="Symbol" field="symbol" />
                      </TableHead>
                      <TableHead className="hidden sm:table-cell">Name</TableHead>
                      <TableHead className="text-right">
                        <SortButton label="Quantity" field="quantity" />
                      </TableHead>
                      <TableHead className="text-right">Avg Cost</TableHead>
                      <TableHead className="text-right">Current Price</TableHead>
                      <TableHead className="text-right">
                        <SortButton label="Market Value" field="market_value" />
                      </TableHead>
                      <TableHead className="text-right">
                        <SortButton label="Gain/Loss" field="unrealized_gains" />
                      </TableHead>
                      <TableHead className="text-right">
                        <SortButton label="Weight" field="weight_percent" />
                      </TableHead>
                      <TableHead className="hidden lg:table-cell">Type</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filtered.map((pos) => (
                      <TableRow key={pos.symbol}>
                        <TableCell className="font-medium sticky left-0 bg-background z-10">
                          {pos.symbol}
                        </TableCell>
                        <TableCell className="hidden sm:table-cell text-muted-foreground text-sm truncate max-w-[200px]">
                          {pos.name}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {pos.quantity.toLocaleString(undefined, { maximumFractionDigits: 4 })}
                        </TableCell>
                        <TableCell className="text-right">
                          <CurrencyText value={pos.average_cost} className="text-sm" />
                        </TableCell>
                        <TableCell className="text-right">
                          <CurrencyText value={pos.current_price} className="text-sm" />
                        </TableCell>
                        <TableCell className="text-right">
                          <CurrencyText value={pos.market_value} className="text-sm font-semibold" />
                        </TableCell>
                        <TableCell className="text-right">
                          <GainLossBadge value={pos.unrealized_gains} />
                        </TableCell>
                        <TableCell className="text-right tabular-nums text-sm text-muted-foreground">
                          {pos.weight_percent.toFixed(1)}%
                        </TableCell>
                        <TableCell className="hidden lg:table-cell">
                          <Badge variant="outline" className="text-xs capitalize">
                            {pos.asset_type}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                    {filtered.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
                          No positions match &ldquo;{search}&rdquo;
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>

          <p className="text-xs text-muted-foreground text-right">
            {filtered.length} of {positions.length} positions
          </p>
        </>
      )}
    </div>
  );
}
