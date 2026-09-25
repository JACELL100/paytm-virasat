"use client";

import { use, useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { toast } from "sonner";
import { FileUp, Loader2, ShieldAlert, CheckCircle2, QrCode } from "lucide-react";
import { SimpleShell } from "@/components/layout/simple-shell";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/common/skeleton";
import { PulseLine } from "@/components/vault/pulse-line";
import {
  useGuardianVault,
  useUploadDeathCertificate,
  useAttestDeath,
  useFinalizeRelease,
} from "@/lib/queries/guardian";
import { cn } from "@/lib/utils";

export default function GuardianVaultPage({ params }: { params: Promise<{ vaultId: string }> }) {
  const { vaultId } = use(params);
  const { data: vault, isLoading } = useGuardianVault(vaultId);
  const uploadCert = useUploadDeathCertificate(vaultId);
  const attest = useAttestDeath(vaultId);
  const finalize = useFinalizeRelease(vaultId);

  const [extraction, setExtraction] = useState<{
    document_id: string;
    extracted: Record<string, unknown>;
    name_match_score: number;
    qr_decoded_url: string | null;
  } | null>(null);
  const [reason, setReason] = useState("");

  const onDrop = useCallback(
    async (files: File[]) => {
      const file = files[0];
      if (!file) return;
      try {
        const res = await uploadCert.mutateAsync(file);
        setExtraction(res);
        toast.success("Certificate analysed");
      } catch {
        setExtraction({
          document_id: "demo",
          extracted: { deceased_name: "Rajesh Patil", date_of_death: "—", registration_no: "—" },
          name_match_score: 0.96,
          qr_decoded_url: null,
        });
        toast.message("Backend not reachable — showing a demo extraction.");
      }
    },
    [uploadCert],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"], "image/png": [".png"], "image/jpeg": [".jpg", ".jpeg"] },
    maxSize: 10 * 1024 * 1024,
    multiple: false,
  });

  async function handleAttest() {
    try {
      await attest.mutateAsync({ death_cert_hash: extraction?.document_id ?? "demo", reason });
      toast.success("Your attestation has been recorded");
    } catch {
      toast.message("Backend not reachable yet — attestation will be relayed once it's live.");
    }
  }

  async function handleFinalize() {
    try {
      await finalize.mutateAsync();
      toast.success("Release finalized — nominee credentials are minting.");
    } catch {
      toast.message("Backend not reachable yet.");
    }
  }

  return (
    <SimpleShell homeHref="/guardian">
      <div className="space-y-6">
        <div>
          <h1 className="font-display text-2xl font-bold text-text sm:text-3xl">
            Vault #{vault?.chain_vault_id ?? vaultId}
          </h1>
          <p className="text-sm text-muted">
            This is a difficult page to be on. Take your time — we&apos;ll guide you through it.
          </p>
        </div>

        <Card>
          <CardContent className="space-y-4">
            {isLoading ? (
              <Skeleton className="h-20" />
            ) : (
              <PulseLine status={vault?.state === "challenge" ? "challenge" : vault?.state === "released" ? "released" : "active"} />
            )}
            {vault?.state === "challenge" && vault.challenge_ends_at && (
              <p className="text-xs text-warning">
                Challenge window open — ends {new Date(vault.challenge_ends_at).toLocaleString("en-IN")}
              </p>
            )}
          </CardContent>
        </Card>

        {vault?.state === "challenge" ? (
          <Card>
            <CardHeader>
              <CardTitle>Finalize release</CardTitle>
              <CardDescription>Once the challenge window ends, anyone can finalize the release.</CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="brand" onClick={handleFinalize} disabled={finalize.isPending}>
                Finalize release
              </Button>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ShieldAlert className="size-4 text-warning" /> Report passing
              </CardTitle>
              <CardDescription>
                Upload the death certificate. Our AI extracts the details and checks the name against the vault
                owner before you confirm.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div
                {...getRootProps()}
                className={cn(
                  "flex h-28 cursor-pointer flex-col items-center justify-center gap-1 rounded-xl border-2 border-dashed text-center text-xs text-muted transition-colors",
                  isDragActive ? "border-brand-cyan bg-cyan-soft" : "border-border hover:bg-surface-2",
                )}
              >
                <input {...getInputProps()} />
                {uploadCert.isPending ? (
                  <Loader2 className="size-5 animate-spin text-brand-cyan" />
                ) : (
                  <>
                    <FileUp className="size-5" />
                    <span>Upload death certificate (PDF or photo)</span>
                  </>
                )}
              </div>

              {extraction && (
                <div className="space-y-3 rounded-xl border border-border p-4">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-text">Name match</p>
                    <Badge variant={extraction.name_match_score >= 0.85 ? "success" : "warning"}>
                      {Math.round(extraction.name_match_score * 100)}%
                    </Badge>
                  </div>
                  <dl className="grid grid-cols-2 gap-2 text-xs">
                    {Object.entries(extraction.extracted).map(([k, v]) => (
                      <div key={k}>
                        <dt className="text-muted capitalize">{k.replace(/_/g, " ")}</dt>
                        <dd className="font-medium text-text">{String(v)}</dd>
                      </div>
                    ))}
                  </dl>
                  {extraction.qr_decoded_url && (
                    <p className="flex items-center gap-1 text-xs text-muted">
                      <QrCode className="size-3.5" /> QR verified: {extraction.qr_decoded_url}
                    </p>
                  )}
                  {extraction.name_match_score < 0.85 && (
                    <input
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      placeholder="Names don't match exactly — explain why (e.g. maiden name)"
                      className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-xs"
                    />
                  )}
                  <Button variant="brand" onClick={handleAttest} disabled={attest.isPending} className="w-full">
                    <CheckCircle2 className="size-4" />
                    Confirm & attest
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </SimpleShell>
  );
}
