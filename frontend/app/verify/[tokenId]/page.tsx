"use client";

import { use } from "react";
import Link from "next/link";
import { ShieldCheck, ExternalLink, XCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/common/skeleton";
import { useVerify } from "@/lib/queries/verify";
import { etherscanTxUrl, formatDateTime, truncateMiddle } from "@/lib/format";

const EXPLORER = process.env.NEXT_PUBLIC_CHAIN_EXPLORER ?? "https://sepolia.etherscan.io";

export default function VerifyPage({ params }: { params: Promise<{ tokenId: string }> }) {
  const { tokenId } = use(params);
  const { data, isLoading, isError } = useVerify(tokenId);

  return (
    <div className="min-h-screen bg-bg">
      <header className="flex h-16 items-center justify-center border-b border-border bg-surface">
        <Link href="/" className="flex items-center gap-2">
          <span className="flex size-8 items-center justify-center rounded-lg brand-gradient text-sm font-bold text-white">
            V
          </span>
          <span className="font-display font-semibold text-text">Paytm Virasat — Verify</span>
        </Link>
      </header>

      <main className="mx-auto max-w-xl px-4 py-10 sm:px-6">
        <Card>
          <CardHeader className="items-center text-center">
            <div className="flex size-12 items-center justify-center rounded-full bg-cyan-soft text-brand-navy dark:text-brand-cyan">
              <ShieldCheck className="size-6" />
            </div>
            <CardTitle>Nominee Credential #{tokenId}</CardTitle>
            <CardDescription>Public, on-chain verification. No personal data is shown here.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {isLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="h-10" />
                ))}
              </div>
            ) : isError || !data ? (
              <div className="flex flex-col items-center gap-2 py-6 text-center text-muted">
                <XCircle className="size-8 text-danger" />
                <p className="text-sm">Could not verify this credential right now.</p>
              </div>
            ) : (
              <>
                <Row label="Valid" value={<Badge variant={data.valid ? "success" : "destructive"}>{data.valid ? "Valid" : "Invalid"}</Badge>} />
                <Row label="Vault ID" value={`#${data.vault_id}`} />
                <Row label="Released at block" value={data.released_at_block.toString()} />
                <Row label="Released at" value={formatDateTime(data.released_at)} />
                <Row label="Share" value={`${(data.share_bps / 100).toFixed(0)}%`} />
                <div>
                  <p className="mb-2 text-xs uppercase tracking-wide text-muted">Claim ledger events</p>
                  <div className="space-y-2">
                    {data.claim_events.map((e, i) => (
                      <div key={i} className="flex items-center justify-between rounded-lg border border-border p-2.5 text-xs">
                        <span className="text-text">{e.status}</span>
                        <a
                          href={etherscanTxUrl(EXPLORER, e.tx_hash)}
                          target="_blank"
                          rel="noreferrer"
                          className="flex items-center gap-1 font-mono-tabular text-brand-cyan hover:underline"
                        >
                          {truncateMiddle(e.tx_hash)}
                          <ExternalLink className="size-3" />
                        </a>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between border-b border-border pb-2 text-sm last:border-0">
      <span className="text-muted">{label}</span>
      <span className="font-medium text-text">{value}</span>
    </div>
  );
}
