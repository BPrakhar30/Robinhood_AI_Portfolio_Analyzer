"use client";
import { useState, useMemo } from "react";
import { ArrowLeftRight } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { TableSkeleton } from "@/components/feedback/loading-skeleton";
import { useTransactions } from "@/features/brokers/hooks";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { CurrencyText } from "@/components/portfolio/currency-text";
import { formatDateShort } from "@/components/portfolio/timestamp-text";

const TXN_COLORS: Record<string, string> = {
  buy: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
  sell: "bg-red-500/10 text-red-700 dark:text-red-400",
  dividend: "bg-blue-500/10 text-blue-700 dark:text-blue-400",
};

export default function TransactionsPage() {
  const { data: transactions, isLoading, error, refetch } = useTransactions(undefined, 200);
  const [typeFilter, setTypeFilter] = useState("all");

  const filtered = useMemo(() => {
    if (!transactions) return [];
    if (typeFilter === "all") return transactions;
    return transactions.filter((t) => t.transaction_type === typeFilter);
  }, [transactions, typeFilter]);

  if (error) {
    return (
      <div>
        <PageHeader title="Transactions" />
        <ErrorState message="Failed to load transactions." onRetry={() => refetch()} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Transactions"
        description="Trade history across all connected accounts"
        actions={
          <Select value={typeFilter} onValueChange={(v) => v && setTypeFilter(v)}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="All types" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All types</SelectItem>
              <SelectItem value="buy">Buy</SelectItem>
              <SelectItem value="sell">Sell</SelectItem>
              <SelectItem value="dividend">Dividend</SelectItem>
            </SelectContent>
          </Select>
        }
      />

      {isLoading ? (
        <TableSkeleton />
      ) : !transactions || transactions.length === 0 ? (
        <EmptyState
          icon={ArrowLeftRight}
          title="No transactions yet"
          description="Transaction history will appear here after you connect a broker and sync your portfolio."
          actionLabel="Connect Broker"
          actionHref="/brokers"
        />
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Symbol</TableHead>
                    <TableHead className="text-right">Quantity</TableHead>
                    <TableHead className="text-right">Price</TableHead>
                    <TableHead className="text-right">Total</TableHead>
                    <TableHead className="text-right">Fees</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.map((txn, i) => (
                    <TableRow key={`${txn.symbol}-${txn.executed_at}-${i}`}>
                      <TableCell className="text-sm tabular-nums text-muted-foreground">
                        {formatDateShort(txn.executed_at)}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="secondary"
                          className={`text-xs capitalize ${TXN_COLORS[txn.transaction_type] || ""}`}
                        >
                          {txn.transaction_type}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-medium">{txn.symbol}</TableCell>
                      <TableCell className="text-right tabular-nums">
                        {txn.quantity.toLocaleString(undefined, { maximumFractionDigits: 4 })}
                      </TableCell>
                      <TableCell className="text-right">
                        <CurrencyText value={txn.price} className="text-sm" />
                      </TableCell>
                      <TableCell className="text-right">
                        <CurrencyText value={txn.total_amount} className="text-sm font-medium" />
                      </TableCell>
                      <TableCell className="text-right text-muted-foreground text-sm tabular-nums">
                        {txn.fees > 0 ? `$${txn.fees.toFixed(2)}` : "—"}
                      </TableCell>
                    </TableRow>
                  ))}
                  {filtered.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                        No transactions match the selected filter.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      <p className="text-xs text-muted-foreground text-right">
        Showing {filtered.length} transaction{filtered.length !== 1 ? "s" : ""}
      </p>
    </div>
  );
}
