"use client";

import { use, useState } from "react";
import { toast } from "sonner";
import { CheckCircle2, Circle, ExternalLink, FileDown, Megaphone } from "lucide-react";
import { SimpleShell } from "@/components/layout/simple-shell";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/common/skeleton";
import { useClaim, useGenerateClaimPack, useDraftEscalation } from "@/lib/queries/claims";
import { formatDateTime, etherscanTxUrl, truncateMiddle } from "@/lib/format";

const EXPLORER = process.env.NEXT_PUBLIC_CHAIN_EXPLORER ?? "https://sepolia.etherscan.io";

const STEPS: Array<{ key: string; label: string }> = [
  { key: "docs_pending", label: "Gathering documents" },
  { key: "ready_to_file", label: "Ready to file" },
  { key: "filed", label: "Filed" },
  { key: "under_review", label: "Under review" },
  { key: "settled", label: "Settled" },
];

export default function ClaimDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: claim, isLoading } = useClaim(id);
  const generatePack = useGenerateClaimPack(id);
  const draftEscalation = useDraftEscalation(id);
  const [packUrl, setPackUrl] = useState<string | null>(null);

  const currentIndex = claim ? STEPS.findIndex((s) => s.key === claim.status) : -1;

  async function handleGeneratePack() {
    try {
      const res = await generatePack.mutateAsync();
      setPackUrl(res.url);
      toast.success("Claim pack ready");
    } catch {
      toast.message("Backend not reachable yet — the PDF will generate once it's live.");
    }
  }

  async function handleEscalate() {
    try {
      await draftEscalation.mutateAsync("gro");
      toast.success("Escalation letter drafted");
    } catch {
      toast.message("Backend not reachable yet.");
    }
  }

  return (
    <SimpleShell homeHref="/nominee">
      <div className="space-y-6">
        {isLoading ? (
          <Skeleton className="h-8 w-56" />
        ) : (
          <div>
            <h1 className="font-display text-2xl font-bold text-text sm:text-3xl">
              {claim?.asset_label ?? "Claim"}
            </h1>
            <p className="text-sm text-muted">{claim?.institution_name}</p>
          </div>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Status</CardTitle>
          </CardHeader>
          <CardContent>
            <ol className="space-y-3">
              {STEPS.map((step, i) => {
                const done = currentIndex >= 0 && i <= currentIndex;
                return (
                  <li key={step.key} className="flex items-center gap-3">
                    {done ? (
                      <CheckCircle2 className="size-5 text-success" />
                    ) : (
                      <Circle className="size-5 text-muted" />
                    )}
                    <span className={done ? "text-text" : "text-muted"}>{step.label}</span>
                  </li>
                );
              })}
            </ol>
            {claim?.sla_due_at && (
              <p className="mt-4 text-xs text-warning">SLA due {formatDateTime(claim.sla_due_at)}</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Document checklist</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {!claim || claim.checklist.length === 0 ? (
              <p className="text-sm text-muted">No checklist yet — ask Sahayak to build one for this claim.</p>
            ) : (
              claim.checklist.map((item, i) => (
                <div key={i} className="flex items-center gap-2 text-sm">
                  {item.done ? (
                    <CheckCircle2 className="size-4 text-success" />
                  ) : (
                    <Circle className="size-4 text-muted" />
                  )}
                  <span className={item.done ? "text-text" : "text-muted"}>{item.label}</span>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Claim pack</CardTitle>
            <CardDescription>A single PDF with everything the institution needs.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-3">
            <Button variant="brand" onClick={handleGeneratePack} disabled={generatePack.isPending}>
              <FileDown className="size-4" /> Generate claim pack
            </Button>
            {packUrl && (
              <Button asChild variant="outline">
                <a href={packUrl} target="_blank" rel="noreferrer">
                  Download PDF
                </a>
              </Button>
            )}
            <Button variant="outline" onClick={handleEscalate} disabled={draftEscalation.isPending}>
              <Megaphone className="size-4" /> Draft escalation
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>On-chain event log</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {!claim || !("events" in claim) || claim.events.length === 0 ? (
              <p className="text-sm text-muted">No on-chain events recorded yet.</p>
            ) : (
              claim.events.map((e) => (
                <div key={e.id} className="flex items-center justify-between rounded-lg border border-border p-2.5 text-xs">
                  <div>
                    <p className="font-medium capitalize text-text">{e.status.replace(/_/g, " ")}</p>
                    <p className="text-muted">{formatDateTime(e.occurred_at)}</p>
                  </div>
                  {e.tx_hash && (
                    <a
                      href={etherscanTxUrl(EXPLORER, e.tx_hash)}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-1 font-mono-tabular text-brand-cyan hover:underline"
                    >
                      {truncateMiddle(e.tx_hash)}
                      <ExternalLink className="size-3" />
                    </a>
                  )}
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {claim?.claim_ref && (
          <Badge variant="outline" className="font-mono-tabular">
            Ref: {claim.claim_ref}
          </Badge>
        )}
      </div>
    </SimpleShell>
  );
}
