"use client";

import Link from "next/link";
import { ShieldCheck, ChevronRight } from "lucide-react";
import { SimpleShell } from "@/components/layout/simple-shell";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/common/skeleton";
import { EmptyState } from "@/components/common/empty-state";
import { useGuardianVaults } from "@/lib/queries/guardian";

export default function GuardianVaultsPage() {
  const { data: vaults, isLoading } = useGuardianVaults();

  return (
    <SimpleShell homeHref="/guardian">
      <div className="space-y-6">
        <div>
          <h1 className="font-display text-2xl font-bold text-text sm:text-3xl">Vaults you guard</h1>
          <p className="text-sm text-muted">
            You&apos;ve been trusted to confirm the unthinkable, only when it truly happens.
          </p>
        </div>

        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 2 }).map((_, i) => (
              <Skeleton key={i} className="h-20" />
            ))}
          </div>
        ) : !vaults || vaults.length === 0 ? (
          <EmptyState
            icon={ShieldCheck}
            title="You aren't guarding any vaults yet"
            body="When someone adds you as a guardian, their vault will appear here."
          />
        ) : (
          vaults.map((v) => (
            <Link key={v.id} href={`/guardian/${v.id}`}>
              <Card className="transition-shadow hover:shadow-[0_4px_28px_rgba(0,46,110,0.14)]">
                <CardContent className="flex items-center justify-between">
                  <div>
                    <p className="font-display font-semibold text-text">Vault #{v.chain_vault_id ?? "—"}</p>
                    <p className="text-xs text-muted">{v.guardians.length} guardians · threshold {v.threshold}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant={v.state === "challenge" ? "warning" : v.state === "released" ? "gold" : "success"}>
                      {v.state}
                    </Badge>
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
