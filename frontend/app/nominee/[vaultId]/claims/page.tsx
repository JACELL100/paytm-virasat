"use client";

import { use } from "react";
import Link from "next/link";
import { ChevronRight, FileClock } from "lucide-react";
import { SimpleShell } from "@/components/layout/simple-shell";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/common/skeleton";
import { EmptyState } from "@/components/common/empty-state";
import { useClaims } from "@/lib/queries/claims";
import type { ClaimStatus } from "@/lib/types";

const STATUS_VARIANT: Record<ClaimStatus, "success" | "warning" | "destructive" | "outline"> = {
  not_started: "outline",
  docs_pending: "warning",
  ready_to_file: "warning",
  filed: "outline",
  under_review: "outline",
  query_raised: "warning",
  settled: "success",
  rejected: "destructive",
  escalated: "destructive",
};

export default function ClaimsListPage({ params }: { params: Promise<{ vaultId: string }> }) {
  const { vaultId } = use(params);
  const { data: claims, isLoading } = useClaims(vaultId);

  return (
    <SimpleShell homeHref={`/nominee/${vaultId}`}>
      <div className="space-y-6">
        <div>
          <h1 className="font-display text-2xl font-bold text-text sm:text-3xl">Claims</h1>
          <p className="text-sm text-muted">Ranked by what matters most, tracked step by step.</p>
        </div>

        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-16" />
            ))}
          </div>
        ) : !claims || claims.length === 0 ? (
          <EmptyState
            icon={FileClock}
            title="No claims yet"
            body="Talk to Sahayak to build your ranked claim plan."
          />
        ) : (
          claims.map((claim) => (
            <Link key={claim.id} href={`/claims/${claim.id}`}>
              <Card className="transition-shadow hover:shadow-[0_4px_28px_rgba(0,46,110,0.14)]">
                <CardContent className="flex items-center justify-between">
                  <div>
                    <p className="font-display font-semibold text-text">{claim.asset_label ?? "Claim"}</p>
                    <p className="text-xs text-muted">{claim.institution_name}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant={STATUS_VARIANT[claim.status]}>{claim.status.replace(/_/g, " ")}</Badge>
                    <ChevronRight className="size-4 text-muted" />
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))
        )}
      </div>
    </SimpleShell>
  );
}
