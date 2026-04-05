"use client";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2, Shield, AlertTriangle } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { cn } from "@/lib/utils";
import { useConnectRobinhood } from "@/features/brokers/hooks";
import { toast } from "sonner";

const schema = z.object({
  username: z.string().min(1, "Username is required"),
  password: z.string().min(1, "Password is required"),
  mfa_code: z.string().optional(),
});

type FormData = z.infer<typeof schema>;

interface Props {
  onSuccess: () => void;
}

export function RobinhoodConnectForm({ onSuccess }: Props) {
  const connectMutation = useConnectRobinhood();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    try {
      await connectMutation.mutateAsync(data);
      toast.success("Robinhood account connected successfully");
      onSuccess();
    } catch (e: any) {
      const msg = e.message || "Connection failed.";
      toast.error(`${msg} You can also try Plaid or CSV import.`);
    }
  };

  return (
    <div className="space-y-4">
      <div className="rounded-lg bg-muted/50 p-3 flex items-start gap-2">
        <Shield className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
        <p className="text-xs text-muted-foreground">
          Your credentials are used only for authentication and are never stored.
          Session tokens are encrypted at rest.
        </p>
      </div>

      <form onSubmit={(e) => { e.preventDefault(); handleSubmit(onSubmit)(); }} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="rh-username">Robinhood Username/Email</Label>
          <Input
            id="rh-username"
            placeholder="your@email.com"
            autoComplete="username"
            {...register("username")}
          />
          {errors.username && (
            <p className="text-xs text-destructive">{errors.username.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="rh-password">Password</Label>
          <Input
            id="rh-password"
            type="password"
            placeholder="••••••••"
            autoComplete="current-password"
            {...register("password")}
          />
          {errors.password && (
            <p className="text-xs text-destructive">{errors.password.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="rh-mfa">MFA Code (if enabled)</Label>
          <Input
            id="rh-mfa"
            placeholder="123456"
            maxLength={6}
            {...register("mfa_code")}
          />
          <p className="text-xs text-muted-foreground">
            Leave blank if you don&apos;t have 2FA enabled.
          </p>
        </div>

        {connectMutation.isError && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription className="text-sm">
              {(connectMutation.error as Error)?.message || "Connection failed."}
              {" "}You can also try{" "}
              <button className="underline font-medium">Plaid</button> or{" "}
              <button className="underline font-medium">CSV import</button>.
            </AlertDescription>
          </Alert>
        )}

        <button type="submit" className={cn(buttonVariants(), "w-full")} disabled={connectMutation.isPending}>
          {connectMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Connect Robinhood
        </button>
      </form>
    </div>
  );
}
