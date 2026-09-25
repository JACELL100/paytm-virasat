"use client";

import { toast } from "sonner";
import { Zap, Coffee } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/common/skeleton";
import { EmptyState } from "@/components/common/empty-state";
import { useActivity, useRecordActivity } from "@/lib/queries/activity";
import { formatDateTime } from "@/lib/format";

export default function ActivityPage() {
  const { data: activity, isLoading } = useActivity();
  const record = useRecordActivity();

  async function simulatePayment() {
    try {
      await record.mutateAsync("upi_payment");
      toast.success("₹40 paid for chai — your heartbeat was recorded");
    } catch {
      toast.message("Backend not reachable yet — this will feed your vault's heartbeat once it's live.");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-text sm:text-3xl">Proof of life</h1>
        <p className="text-sm text-muted">
          Your everyday Paytm activity automatically keeps your vault&apos;s heartbeat going.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Zap className="size-4 text-brand-cyan" /> Demo simulator
          </CardTitle>
          <CardDescription>
            In the real app, any Paytm login or payment counts. Use this to simulate one for the demo.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="brand" onClick={simulatePayment} disabled={record.isPending}>
            <Coffee className="size-4" />
            Pay ₹40 for chai
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Activity log</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {isLoading ? (
            Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-10" />)
          ) : !activity || activity.length === 0 ? (
            <EmptyState title="No activity recorded yet" />
          ) : (
            activity.map((event) => (
              <div key={event.id} className="flex items-center justify-between border-b border-border py-2 text-sm last:border-0">
                <span className="capitalize text-text">{event.kind.replace("_", " ")}</span>
                <span className="font-mono-tabular text-xs text-muted">{formatDateTime(event.occurred_at)}</span>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
