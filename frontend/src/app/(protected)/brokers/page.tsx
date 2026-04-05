"use client";
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Link as LinkIcon, Plus, RefreshCw, Trash2, Upload, Shield } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { useConnections, useDisconnectBroker, useSyncConnection } from "@/features/brokers/hooks";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { BrokerBadge, StatusBadge } from "@/components/portfolio/broker-badge";
import { TimestampText } from "@/components/portfolio/timestamp-text";
import { Skeleton } from "@/components/ui/skeleton";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
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

  const { data: connections, isLoading, error, refetch } = useConnections();
  const disconnectMutation = useDisconnectBroker();
  const syncMutation = useSyncConnection();

  const handleDisconnect = async (id: number) => {
    await disconnectMutation.mutateAsync(id);
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
                    <AlertDialog>
                      <AlertDialogTrigger
                        className="inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium rounded-md border border-input bg-background h-8 px-3 text-destructive hover:text-destructive hover:bg-accent cursor-pointer"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        Disconnect
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Disconnect this broker?</AlertDialogTitle>
                          <AlertDialogDescription>
                            This will remove the connection and clear stored tokens.
                            Your imported data will remain until you delete it.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                            onClick={() => handleDisconnect(conn.id)}
                          >
                            Disconnect
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
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
                <button onClick={() => setConnectFlow("plaid")} className="underline hover:text-foreground">
                  Plaid
                </button>{" "}
                for automatic account linking, or{" "}
                <button onClick={() => setConnectFlow("csv")} className="underline hover:text-foreground">
                  import a CSV
                </button>{" "}
                file as a fallback. All tokens are encrypted at rest.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

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
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Import from CSV</DialogTitle>
          </DialogHeader>
          <CSVImportForm onSuccess={() => setConnectFlow(null)} />
        </DialogContent>
      </Dialog>
    </div>
  );
}
