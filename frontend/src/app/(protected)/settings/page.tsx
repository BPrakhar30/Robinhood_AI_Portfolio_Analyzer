"use client";
import { useState } from "react";
import { useAuthStore } from "@/features/auth/store";
import { useLogout, useDeleteAccount } from "@/features/auth/hooks";
import { useStatus } from "@/features/system/hooks";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/portfolio/broker-badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { LogOut, Trash2, AlertTriangle, Loader2 } from "lucide-react";

export default function SettingsPage() {
  const { user } = useAuthStore();
  const logout = useLogout();
  const deleteAccountMutation = useDeleteAccount();
  const { data: status } = useStatus();
  const [dialogOpen, setDialogOpen] = useState(false);

  const handleDeleteAccount = async () => {
    try {
      await deleteAccountMutation.mutateAsync();
    } catch {
      // error shown inline
    }
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <PageHeader title="Settings" description="Manage your account and preferences" />

      {/* Profile */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Profile</CardTitle>
          <CardDescription>Your account information</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Name</p>
              <p className="text-sm font-medium">{user?.full_name || "—"}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Email</p>
              <p className="text-sm font-medium">{user?.email}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Member since</p>
              <p className="text-sm font-medium">
                {user?.created_at
                  ? new Date(user.created_at).toLocaleDateString("en-US", {
                      month: "long",
                      day: "numeric",
                      year: "numeric",
                    })
                  : "—"}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Status</p>
              <StatusBadge status={user?.is_active ? "active" : "inactive"} />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* System diagnostics */}
      {status && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">System Diagnostics</CardTitle>
            <CardDescription>Backend service health</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">API</p>
                <StatusBadge status={status.components.api} />
              </div>
              <div>
                <p className="text-muted-foreground">Database</p>
                <StatusBadge status={status.components.database} />
              </div>
              <div>
                <p className="text-muted-foreground">Version</p>
                <p className="font-mono text-xs">{status.version}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Overall</p>
                <StatusBadge status={status.status} />
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Session */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Session</CardTitle>
        </CardHeader>
        <CardContent>
          <Button variant="destructive" onClick={logout}>
            <LogOut className="mr-2 h-4 w-4" />
            Log out
          </Button>
        </CardContent>
      </Card>

      {/* Delete Account */}
      <Card className="border-destructive/30">
        <CardHeader>
          <CardTitle className="text-base text-destructive">Danger Zone</CardTitle>
          <CardDescription>
            Permanently delete your account and all associated data
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            This will permanently remove your account, broker connections, portfolio
            data, and transaction history. This action cannot be undone.
          </p>

          {deleteAccountMutation.isError && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription className="text-sm">
                {(deleteAccountMutation.error as Error)?.message ||
                  "Failed to delete account. Please try again."}
              </AlertDescription>
            </Alert>
          )}

          <Button
            variant="destructive"
            className="gap-2"
            onClick={() => setDialogOpen(true)}
          >
            <Trash2 className="h-4 w-4" />
            Delete Account
          </Button>

          <AlertDialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Are you sure?</AlertDialogTitle>
                <AlertDialogDescription>
                  This will permanently delete your account, all broker connections,
                  positions, transactions, and portfolio snapshots. This action
                  cannot be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel disabled={deleteAccountMutation.isPending}>
                  Cancel
                </AlertDialogCancel>
                <AlertDialogAction
                  onClick={handleDeleteAccount}
                  disabled={deleteAccountMutation.isPending}
                  className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                >
                  {deleteAccountMutation.isPending && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  Yes, delete my account
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </CardContent>
      </Card>
    </div>
  );
}
