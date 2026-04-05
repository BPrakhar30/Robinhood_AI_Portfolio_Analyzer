"use client";
import { useAuthStore } from "@/features/auth/store";
import { useLogout } from "@/features/auth/hooks";
import { useStatus } from "@/features/system/hooks";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { StatusBadge } from "@/components/portfolio/broker-badge";
import { LogOut } from "lucide-react";

export default function SettingsPage() {
  const { user } = useAuthStore();
  const logout = useLogout();
  const { data: status } = useStatus();

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

      {/* Logout */}
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
    </div>
  );
}
