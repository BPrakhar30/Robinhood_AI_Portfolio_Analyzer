"use client";
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Link as LinkIcon, Plus, RefreshCw, Trash2, Upload, Shield, Unplug, Loader2 } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { useConnections, useDisconnectBroker, useDeleteConnection, useSyncConnection } from "@/features/brokers/hooks";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { BrokerBadge, StatusBadge } from "@/components/portfolio/broker-badge";
import { TimestampText } from "@/components/portfolio/timestamp-text";
import { Skeleton } from "@/components/ui/skeleton";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { RobinhoodConnectForm } from "./robinhood-connect";
import { CSVImportForm } from "./csv-import";

type ConnectFlow = "robinhood" | "plaid" | "csv" | null;

export default function BrokersPage() {
  return (
    <Suspense>
      <BrokersContent />
    </Suspense>
  );
}

function BrokersContent() {
  const searchParams = useSearchParams();
  const initialFlow = searchParams.get("connect") as ConnectFlow;
  const [connectFlow, setConnectFlow] = useState<ConnectFlow>(initialFlow);
  const [disconnectId, setDisconnectId] = useState<number | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  const { data: connections, isLoading, error, refetch } = useConnections();
  const disconnectMutation = useDisconnectBroker();
  const deleteMutation = useDeleteConnection();
  const syncMutation = useSyncConnection();

  const isBusy = disconnectMutation.isPending || deleteMutation.isPending;

  const handleDisconnect = async (id: number) => {
    await disconnectMutation.mutateAsync(id);
    setDisconnectId(null);
  };

  const handleDeleteClick = (id: number) => {
    setDisconnectId(null);
    setConfirmDeleteId(id);
  };

  const handleDeleteConfirm = async (id: number) => {
    await deleteMutation.mutateAsync(id);
    setConfirmDeleteId(null);
  };

  const handleSync = async (id: number) => {
    await syncMutation.mutateAsync(id);
  };

  if (error) {
    return (
      <div>
        <PageHeader title="Broker Connections" />
        <ErrorState message="Failed to load broker connections." onRetry={() => refetch()} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Broker Connections"
        description="Manage your linked brokerage accounts and data sources"
        actions={
          <Button onClick={() => setConnectFlow("robinhood")}>
            <Plus className="mr-2 h-4 w-4" />
            Connect Broker
          </Button>
        }
      />

      {isLoading ? (
        <div className="space-y-3">
          {[1, 2].map((i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      ) : connections && connections.length > 0 ? (
        <div className="space-y-3">
          {connections.map((conn) => (
            <Card key={conn.id}>
              <CardContent className="p-5">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="flex items-center gap-4">
                    <div className="rounded-lg bg-muted p-2.5">
                      <LinkIcon className="h-5 w-5 text-muted-foreground" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <BrokerBadge brokerType={conn.broker_type} />
                        <StatusBadge status={conn.status} />
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Connected: <TimestampText date={conn.created_at} /> &middot;
                        Last sync: <TimestampText date={conn.last_sync_at} />
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleSync(conn.id)}
                      disabled={syncMutation.isPending || conn.status === "disconnected"}
                    >
                      <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${syncMutation.isPending ? "animate-spin" : ""}`} />
                      Sync
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-destructive hover:text-destructive"
                      onClick={() => setDisconnectId(conn.id)}
                    >
                      <Unplug className="h-3.5 w-3.5 mr-1.5" />
                      Disconnect
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={LinkIcon}
          title="No broker connections"
          description="Connect your first account to start importing positions and transaction history."
          actionLabel="Connect Broker"
          onAction={() => setConnectFlow("robinhood")}
        />
      )}

      {/* Fallback note */}
      <Card className="bg-muted/30 border-dashed">
        <CardContent className="p-5">
          <div className="flex items-start gap-3">
            <Shield className="h-5 w-5 text-muted-foreground mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-medium">Multiple import options available</p>
              <p className="text-xs text-muted-foreground mt-1">
                Robinhood unavailable? Use{" "}
                <button onClick={() => setConnectFlow("plaid")} className="underline hover:text-foreground cursor-pointer">
                  Plaid
                </button>{" "}
                for automatic account linking, or{" "}
                <button onClick={() => setConnectFlow("csv")} className="underline hover:text-foreground cursor-pointer">
                  import a CSV
                </button>{" "}
                file as a fallback. All tokens are encrypted at rest.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Disconnect / Delete dialog */}
      <Dialog open={disconnectId !== null} onOpenChange={(o) => !o && !isBusy && setDisconnectId(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Disconnect this broker?</DialogTitle>
          </DialogHeader>

          <div className="space-y-3 py-2">
            {/* Option 1: Disconnect only (highlighted) */}
            <button
              type="button"
              onClick={() => disconnectId && handleDisconnect(disconnectId)}
              disabled={isBusy}
              className="w-full rounded-lg border-2 border-destructive/40 p-4 text-left transition-colors hover:bg-muted/50 disabled:opacity-50 cursor-pointer"
            >
              <div className="flex items-start gap-3">
                <Unplug className="h-5 w-5 text-destructive mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-medium text-destructive flex items-center gap-2">
                    Disconnect
                    {disconnectMutation.isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Revoke the live connection and clear stored tokens. Your imported
                    positions, transactions, and portfolio history will be kept, and
                    AI features will continue to work on your existing data.
                  </p>
                </div>
              </div>
            </button>

            {/* Option 2: Disconnect & delete data (subdued) */}
            <button
              type="button"
              onClick={() => disconnectId && handleDeleteClick(disconnectId)}
              disabled={isBusy}
              className="w-full rounded-lg border border-border p-4 text-left transition-colors hover:bg-muted/50 disabled:opacity-50 cursor-pointer"
            >
              <div className="flex items-start gap-3">
                <Trash2 className="h-5 w-5 text-muted-foreground mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                    Disconnect & Delete Data
                    {deleteMutation.isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Remove the connection and permanently delete all imported positions,
                    transactions, and portfolio snapshots. AI features will not work
                    without data.
                  </p>
                </div>
              </div>
            </button>
          </div>

          <div className="flex justify-end">
            <Button variant="ghost" onClick={() => setDisconnectId(null)} disabled={isBusy}>
              Cancel
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Delete confirmation (second step) */}
      <Dialog open={confirmDeleteId !== null} onOpenChange={(o) => !o && !deleteMutation.isPending && setConfirmDeleteId(null)}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Are you sure?</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <p className="text-sm text-muted-foreground">
              Deleting is permanent - all your data for this broker will be removed
              and cannot be recovered.
            </p>
          </div>
          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              onClick={() => {
                setConfirmDeleteId(null);
                setDisconnectId(confirmDeleteId);
              }}
              disabled={deleteMutation.isPending}
            >
              Go back
            </Button>
            <Button
              variant="destructive"
              onClick={() => confirmDeleteId && handleDeleteConfirm(confirmDeleteId)}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Delete my data
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Connect flow dialogs */}
      <Dialog open={connectFlow === "robinhood"} onOpenChange={(o) => !o && setConnectFlow(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Connect Robinhood</DialogTitle>
          </DialogHeader>
          <RobinhoodConnectForm onSuccess={() => setConnectFlow(null)} />
        </DialogContent>
      </Dialog>

      <Dialog open={connectFlow === "plaid"} onOpenChange={(o) => !o && setConnectFlow(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Connect via Plaid</DialogTitle>
          </DialogHeader>
          <div className="py-4 space-y-4">
            <p className="text-sm text-muted-foreground">
              Plaid integration allows automatic linking of your investment accounts.
              When configured, a secure Plaid Link session will open to connect your broker.
            </p>
            <div className="rounded-lg bg-amber-500/10 border border-amber-500/20 p-3">
              <p className="text-xs text-amber-700 dark:text-amber-400">
                Plaid requires server-side configuration. Contact your administrator to set up
                Plaid credentials, or use CSV import as an alternative.
              </p>
            </div>
            <Button variant="outline" className="w-full" onClick={() => setConnectFlow("csv")}>
              <Upload className="mr-2 h-4 w-4" />
              Use CSV import instead
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={connectFlow === "csv"} onOpenChange={(o) => !o && setConnectFlow(null)}>
        <DialogContent className="sm:max-w-lg min-w-0">
          <DialogHeader className="min-w-0">
            <DialogTitle>Import from CSV</DialogTitle>
          </DialogHeader>
          <div className="min-w-0 overflow-x-hidden">
            <CSVImportForm onSuccess={() => setConnectFlow(null)} />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
