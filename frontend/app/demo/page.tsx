"use client";

import { useState } from "react";
import { toast } from "sonner";
import { TimerReset, Zap, RefreshCw, Rewind } from "lucide-react";
import { SimpleShell } from "@/components/layout/simple-shell";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ComingSoon } from "@/components/common/coming-soon";
import { api } from "@/lib/api";

const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

export default function DemoPage() {
  if (!DEMO_MODE) {
    return (
      <SimpleShell>
        <ComingSoon
          title="Demo panel disabled"
          description="Set NEXT_PUBLIC_DEMO_MODE=true to enable the time-warp controls."
        />
      </SimpleShell>
    );
  }
  return (
    <SimpleShell>
      <DemoControls />
    </SimpleShell>
  );
}

function DemoControls() {
  const [pending, setPending] = useState<string | null>(null);

  async function trigger(label: string, path: string) {
    setPending(label);
    try {
      await api.post(`/demo/${path}`);
      toast.success(`${label} triggered`);
    } catch {
      toast.message(`${label} would run once the backend is connected.`);
    } finally {
      setPending(null);
    }
  }

  const actions = [
    { key: "shrink-periods", label: "Shrink periods to seconds", icon: TimerReset },
    { key: "force-heartbeat", label: "Force a heartbeat batch", icon: Zap },
    { key: "sync-events", label: "Trigger on-chain event sync", icon: RefreshCw },
    { key: "reset-persona", label: "Reset demo persona (Rajesh Patil)", icon: Rewind },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <h1 className="font-display text-2xl font-bold text-text sm:text-3xl">Demo control panel</h1>
        <Badge variant="warning">Demo mode</Badge>
      </div>
      <p className="text-sm text-muted">
        Time-warp the inactivity and challenge periods, force background jobs, and reset the seeded persona for a
        clean run before you present.
      </p>

      <div className="grid gap-4 sm:grid-cols-2">
        {actions.map((a) => (
          <Card key={a.key}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <a.icon className="size-4 text-brand-cyan" /> {a.label}
              </CardTitle>
              <CardDescription>Calls POST /demo/{a.key}</CardDescription>
            </CardHeader>
            <CardContent>
              <Button
                variant="outline"
                className="w-full"
                onClick={() => trigger(a.label, a.key)}
                disabled={pending === a.label}
              >
                {pending === a.label ? "Running…" : "Run"}
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
