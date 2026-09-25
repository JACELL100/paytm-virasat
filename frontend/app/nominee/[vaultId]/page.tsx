"use client";

import { use } from "react";
import Link from "next/link";
import { Award, MessageCircleHeart, FileClock } from "lucide-react";
import { SimpleShell } from "@/components/layout/simple-shell";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/common/skeleton";
import { PulseLine } from "@/components/vault/pulse-line";
import { LegacyKeyUnlock } from "@/components/nominee/legacy-key-unlock";
import { useNomineeVault } from "@/lib/queries/nominee";

export default function NomineeVaultPage({ params }: { params: Promise<{ vaultId: string }> }) {
  const { vaultId } = use(params);
  const { data: vault, isLoading } = useNomineeVault(vaultId);
  const released = vault?.state === "released";

  return (
    <SimpleShell homeHref="/nominee">
      <div className="space-y-6">
        <div>
          <h1 className="font-display text-2xl font-bold text-text sm:text-3xl">
            Vault #{vault?.chain_vault_id ?? vaultId}
          </h1>
          <p className="text-sm text-muted">
            {released
              ? "Your family's Virasat is ready. Take your time."
              : "This vault is still active and protected."}
          </p>
        </div>

        <Card>
          <CardContent>
            {isLoading ? <Skeleton className="h-20" /> : <PulseLine status={released ? "released" : "active"} />}
          </CardContent>
        </Card>

        {released ? (
          <>
            <Card className="overflow-hidden">
              <div className="brand-gradient p-6 text-white">
                <div className="flex items-center gap-2 text-sm text-white/80">
                  <Award className="size-4" /> Nominee Credential
                </div>
                <p className="mt-2 font-display text-xl font-bold">Soulbound · Virasat #{vaultId}</p>
                <p className="mt-1 text-xs text-white/70">
                  A permanent, tamper-proof record that you are a verified nominee of this vault.
                </p>
              </div>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Unlock with your Legacy Key</CardTitle>
                <CardDescription>
                  Scan the QR from your Legacy Key card, or paste the key you were given at invite time.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <LegacyKeyUnlock vaultId={vaultId} />
              </CardContent>
            </Card>

            <div className="grid gap-4 sm:grid-cols-2">
              <Link href={`/nominee/${vaultId}/copilot`}>
                <Card className="h-full transition-shadow hover:shadow-[0_4px_28px_rgba(0,46,110,0.14)]">
                  <CardContent className="flex items-center gap-3">
                    <MessageCircleHeart className="size-6 text-brand-cyan" />
                    <div>
                      <p className="font-display font-semibold text-text">Talk to Sahayak</p>
                      <p className="text-xs text-muted">Your voice-first claim co-pilot</p>
                    </div>
                  </CardContent>
                </Card>
              </Link>
              <Link href={`/nominee/${vaultId}/claims`}>
                <Card className="h-full transition-shadow hover:shadow-[0_4px_28px_rgba(0,46,110,0.14)]">
                  <CardContent className="flex items-center gap-3">
                    <FileClock className="size-6 text-brand-cyan" />
                    <div>
                      <p className="font-display font-semibold text-text">Track claims</p>
                      <p className="text-xs text-muted">See status, SLAs and documents</p>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            </div>
          </>
        ) : (
          <Card>
            <CardContent className="py-10 text-center text-sm text-muted">
              This vault becomes available to you once it&apos;s released. We&apos;ll email you when that happens.
              <div className="mt-4">
                <Button variant="outline" disabled>
                  Waiting for release
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </SimpleShell>
  );
}
