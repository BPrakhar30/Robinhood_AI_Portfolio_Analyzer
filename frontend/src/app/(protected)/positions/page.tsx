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
import { GainLossDisplay } from "@/components/portfolio/gain-loss-display";
import { Badge } from "@/components/ui/badge";

type SortKey = "symbol" | "market_value" | "unrealized_gains" | "weight_percent" | "quantity" | "total_amount_invested";
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

  const formatQuantity = (value: number) =>
    value.toLocaleString(undefined, { maximumFractionDigits: 4 });

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

          {/* Mobile cards */}
          <Card>
            <CardContent className="p-0">
              <div className="divide-y md:hidden">
                {filtered.map((pos) => (
                  <div key={pos.symbol} className="space-y-4 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 space-y-1">
                        <div className="flex items-center gap-2">
                          <p className="font-semibold">{pos.symbol}</p>
                          <Badge variant="outline" className="text-[10px] capitalize">
                            {pos.asset_type}
                          </Badge>
                        </div>
                        <p className="truncate text-sm text-muted-foreground">{pos.name}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-muted-foreground">Market Value</p>
                        <CurrencyText value={pos.market_value} className="text-sm font-semibold" />
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div>
                        <p className="text-xs text-muted-foreground">Quantity</p>
                        <p className="tabular-nums">{formatQuantity(pos.quantity)}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-muted-foreground">Weight</p>
                        <p className="tabular-nums">{pos.weight_percent.toFixed(1)}%</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Avg Cost</p>
                        <CurrencyText value={pos.average_cost} className="text-sm" />
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-muted-foreground">Current Price</p>
                        <CurrencyText value={pos.current_price} className="text-sm" />
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Invested</p>
                        <CurrencyText value={pos.total_amount_invested} className="text-sm" />
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-muted-foreground">Gain/Loss</p>
                        <GainLossDisplay
                          value={pos.unrealized_gains}
                          invested={pos.total_amount_invested}
                          align="right"
                        />
                      </div>
                    </div>
                  </div>
                ))}
                {filtered.length === 0 && (
                  <div className="py-8 text-center text-muted-foreground">
                    No positions match &ldquo;{search}&rdquo;
                  </div>
                )}
              </div>

              <div className="hidden md:block">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>
                        <SortButton label="Symbol" field="symbol" />
                      </TableHead>
                      <TableHead className="text-right">
                        <SortButton label="Quantity" field="quantity" />
                      </TableHead>
                      <TableHead className="text-right">Price</TableHead>
                      <TableHead className="text-right">
                        <SortButton label="Invested" field="total_amount_invested" />
                      </TableHead>
                      <TableHead className="text-right">
                        <SortButton label="Market Value" field="market_value" />
                      </TableHead>
                      <TableHead className="text-right">
                        <SortButton label="Gain/Loss" field="unrealized_gains" />
                      </TableHead>
                      <TableHead className="text-right">
                        <SortButton label="Weight" field="weight_percent" />
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filtered.map((pos) => (
                      <TableRow key={pos.symbol}>
                        <TableCell className="align-top">
                          <div className="min-w-0 space-y-1">
                            <p className="font-medium">{pos.symbol}</p>
                            <p className="max-w-[220px] truncate text-sm text-muted-foreground">
                              {pos.name}
                            </p>
                            <Badge variant="outline" className="text-[10px] capitalize">
                              {pos.asset_type}
                            </Badge>
                          </div>
                        </TableCell>
                        <TableCell className="text-right tabular-nums align-top">
                          {formatQuantity(pos.quantity)}
                        </TableCell>
                        <TableCell className="text-right align-top">
                          <div className="space-y-1 text-sm">
                            <div>
                              <span className="mr-2 text-xs text-muted-foreground">Avg</span>
                              <CurrencyText value={pos.average_cost} className="text-sm" />
                            </div>
                            <div>
                              <span className="mr-2 text-xs text-muted-foreground">Now</span>
                              <CurrencyText value={pos.current_price} className="text-sm" />
                            </div>
                          </div>
                        </TableCell>
                        <TableCell className="text-right align-top">
                          <CurrencyText value={pos.total_amount_invested} className="text-sm" />
                        </TableCell>
                        <TableCell className="text-right align-top">
                          <CurrencyText value={pos.market_value} className="text-sm font-semibold" />
                        </TableCell>
                        <TableCell className="text-right align-top">
                          <GainLossDisplay
                            value={pos.unrealized_gains}
                            invested={pos.total_amount_invested}
                            align="right"
                          />
                        </TableCell>
                        <TableCell className="text-right tabular-nums text-sm text-muted-foreground align-top">
                          {pos.weight_percent.toFixed(1)}%
                        </TableCell>
                      </TableRow>
                    ))}
                    {filtered.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
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
