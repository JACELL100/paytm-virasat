"use client";

import Link from "next/link";
import { HeartHandshake, ChevronRight } from "lucide-react";
import { SimpleShell } from "@/components/layout/simple-shell";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/common/skeleton";
import { EmptyState } from "@/components/common/empty-state";
import { useNomineeVaults } from "@/lib/queries/nominee";

export default function NomineeVaultsPage() {
  const { data: vaults, isLoading } = useNomineeVaults();

  return (
    <SimpleShell homeHref="/nominee">
      <div className="space-y-6">
        <div>
          <h1 className="font-display text-2xl font-bold text-text sm:text-3xl">Your Virasat</h1>
          <p className="text-sm text-muted">Vaults where you&apos;ve been named as a nominee.</p>
        </div>

        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 2 }).map((_, i) => (
              <Skeleton key={i} className="h-20" />
            ))}
          </div>
        ) : !vaults || vaults.length === 0 ? (
          <EmptyState
            icon={HeartHandshake}
            title="No vaults yet"
            body="When someone names you as a nominee, their vault will appear here."
          />
        ) : (
          vaults.map((v) => (
            <Link key={v.id} href={`/nominee/${v.id}`}>
              <Card className="transition-shadow hover:shadow-[0_4px_28px_rgba(0,46,110,0.14)]">
                <CardContent className="flex items-center justify-between">
                  <div>
                    <p className="font-display font-semibold text-text">Vault #{v.chain_vault_id ?? "—"}</p>
                    <p className="text-xs text-muted">{v.nominees.length} nominees</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant={v.state === "released" ? "gold" : "outline"}>{v.state}</Badge>
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
