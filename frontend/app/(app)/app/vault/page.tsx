"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { Plus, ShieldCheck, Users, UserCheck, Clock, ExternalLink } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/common/skeleton";
import { EmptyState } from "@/components/common/empty-state";
import { VaultSeal } from "@/components/vault/vault-seal";
import { PulseLine } from "@/components/vault/pulse-line";
import { useVault, useCreateVault, useCancelRelease, useInviteNominee, useInviteGuardian } from "@/lib/queries/vault";
import { formatDateTime, etherscanTxUrl, truncateMiddle } from "@/lib/format";

const EXPLORER = process.env.NEXT_PUBLIC_CHAIN_EXPLORER ?? "https://sepolia.etherscan.io";

const nomineeSchema = z.object({
  name: z.string().min(2, "Enter a name"),
  relation: z.string().min(2, "Enter a relation"),
  email: z.string().email("Enter a valid email"),
  share_bps: z.number().min(1).max(10000),
});
type NomineeForm = z.infer<typeof nomineeSchema>;

const guardianSchema = z.object({
  name: z.string().min(2, "Enter a name"),
  relation: z.string().min(2, "Enter a relation"),
  email: z.string().email("Enter a valid email"),
});
type GuardianForm = z.infer<typeof guardianSchema>;

export default function VaultPage() {
  const { data: vault, isLoading } = useVault();
  const createVault = useCreateVault();
  const cancelRelease = useCancelRelease();
  const [sealOpen, setSealOpen] = useState(false);
  const [sealState, setSealState] = useState<"idle" | "sealing" | "sealed">("idle");
  const [txHash, setTxHash] = useState<string | null>(null);

  async function handleSeal() {
    setSealOpen(true);
    setSealState("sealing");
    try {
      const res = await createVault.mutateAsync({
        inactivity_secs: 60 * 60 * 24 * 180,
        challenge_secs: 60 * 60 * 24 * 14,
        threshold: 2,
      });
      setTxHash(res.txHash);
      setSealState("sealed");
      toast.success("Your Virasat vault is sealing on Sepolia");
    } catch {
      setTxHash("0xDEMO0000000000000000000000000000000000000000000000000000000001");
      setSealState("sealed");
      toast.message("Backend not reachable — showing a demo seal animation.");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <h1 className="font-display text-2xl font-bold text-text sm:text-3xl">Your Virasat vault</h1>
        <p className="text-sm text-muted">
          Add nominees and guardians, tune the protection periods, then seal everything on-chain.
        </p>
      </div>

      <Card>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-muted">Status</p>
              {isLoading ? (
                <Skeleton className="mt-1 h-6 w-32" />
              ) : (
                <p className="font-display text-lg font-semibold capitalize text-text">
                  {vault?.state ?? "draft"}
                </p>
              )}
            </div>
            {vault?.state === "challenge" ? (
              <Button variant="destructive" onClick={() => cancelRelease.mutate()}>
                I&apos;m well — cancel release
              </Button>
            ) : (
              <Dialog open={sealOpen} onOpenChange={setSealOpen}>
                <DialogTrigger asChild>
                  <Button variant="brand" onClick={handleSeal} disabled={sealState === "sealing"}>
                    <ShieldCheck className="size-4" />
                    Seal my Virasat
                  </Button>
                </DialogTrigger>
                <DialogContent className="flex flex-col items-center text-center">
                  <DialogHeader>
                    <DialogTitle>Sealing your Virasat</DialogTitle>
                  </DialogHeader>
                  <VaultSeal
                    state={sealState}
                    txHash={txHash}
                    caption={
                      sealState === "sealing"
                        ? "Encrypting your manifest and signing on-chain…"
                        : undefined
                    }
                  />
                  {sealState === "sealed" && (
                    <p className="text-sm text-muted">
                      Your vault is now protected. Nominees and guardians will be notified.
                    </p>
                  )}
                </DialogContent>
              </Dialog>
            )}
          </div>
          <PulseLine
            status={
              vault?.state === "challenge" ? "challenge" : vault?.state === "released" ? "released" : "active"
            }
          />
        </CardContent>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        <NomineesCard vaultLoaded={!!vault} nominees={vault?.nominees ?? []} loading={isLoading} />
        <GuardiansCard
          vaultLoaded={!!vault}
          guardians={vault?.guardians ?? []}
          threshold={vault?.threshold ?? 2}
          loading={isLoading}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="size-4" /> Protection periods
          </CardTitle>
          <CardDescription>
            How long the vault waits for inactivity, and how long the challenge window stays open before release.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-xl border border-border p-4">
            <p className="text-xs text-muted">Inactivity period</p>
            <p className="font-display text-lg font-semibold text-text">
              {formatSeconds(vault?.inactivity_secs ?? 60 * 60 * 24 * 180)}
            </p>
          </div>
          <div className="rounded-xl border border-border p-4">
            <p className="text-xs text-muted">Challenge period</p>
            <p className="font-display text-lg font-semibold text-text">
              {formatSeconds(vault?.challenge_secs ?? 60 * 60 * 24 * 14)}
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>On-chain timeline</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-12" />
              ))}
            </div>
          ) : !vault || vault.timeline.length === 0 ? (
            <EmptyState title="No on-chain events yet" body="Seal your vault to start the timeline." />
          ) : (
            <ol className="space-y-3">
              {vault.timeline.map((event) => (
                <li key={event.id} className="flex items-center justify-between gap-3 rounded-lg border border-border p-3 text-sm">
                  <div>
                    <p className="font-medium text-text">{event.event}</p>
                    <p className="text-xs text-muted">{formatDateTime(event.occurred_at)}</p>
                  </div>
                  {event.tx_hash && (
                    <a
                      href={etherscanTxUrl(EXPLORER, event.tx_hash)}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-1 font-mono-tabular text-xs text-brand-cyan hover:underline"
                    >
                      {truncateMiddle(event.tx_hash)}
                      <ExternalLink className="size-3" />
                    </a>
                  )}
                </li>
              ))}
            </ol>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function formatSeconds(secs: number) {
  const days = Math.round(secs / 86400);
  return days >= 1 ? `${days} day${days === 1 ? "" : "s"}` : `${secs} sec`;
}

function NomineesCard({
  nominees,
  loading,
}: {
  vaultLoaded: boolean;
  nominees: NonNullable<ReturnType<typeof useVault>["data"]>["nominees"];
  loading: boolean;
}) {
  const [open, setOpen] = useState(false);
  const invite = useInviteNominee();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<NomineeForm>({ resolver: zodResolver(nomineeSchema) });

  async function onSubmit(values: NomineeForm) {
    try {
      await invite.mutateAsync(values);
      toast.success(`Invite sent to ${values.name}`);
      reset();
      setOpen(false);
    } catch {
      toast.error("Could not send invite — check the backend connection.");
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="flex items-center gap-2">
            <UserCheck className="size-4" /> Nominees
          </CardTitle>
          <CardDescription>Who receives each asset&apos;s share.</CardDescription>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button size="sm" variant="outline">
              <Plus className="size-4" /> Add
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Invite a nominee</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
              <div className="space-y-1.5">
                <Label htmlFor="n-name">Full name</Label>
                <Input id="n-name" {...register("name")} />
                {errors.name && <p className="text-xs text-danger">{errors.name.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="n-relation">Relation</Label>
                <Input id="n-relation" placeholder="Spouse, son, daughter…" {...register("relation")} />
                {errors.relation && <p className="text-xs text-danger">{errors.relation.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="n-email">Email</Label>
                <Input id="n-email" type="email" {...register("email")} />
                {errors.email && <p className="text-xs text-danger">{errors.email.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="n-share">Share (%)</Label>
                <Input
                  id="n-share"
                  type="number"
                  defaultValue={50}
                  {...register("share_bps", { valueAsNumber: true })}
                />
                {errors.share_bps && <p className="text-xs text-danger">{errors.share_bps.message}</p>}
              </div>
              <DialogFooter>
                <Button type="submit" variant="brand" disabled={isSubmitting}>
                  Send invite
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </CardHeader>
      <CardContent className="space-y-2">
        {loading ? (
          Array.from({ length: 2 }).map((_, i) => <Skeleton key={i} className="h-14" />)
        ) : nominees.length === 0 ? (
          <EmptyState icon={Users} title="No nominees yet" body="Add at least one nominee to seal your vault." />
        ) : (
          nominees.map((n) => (
            <div key={n.id} className="flex items-center justify-between rounded-lg border border-border p-3">
              <div>
                <p className="text-sm font-medium text-text">{n.name}</p>
                <p className="text-xs text-muted">
                  {n.relation} · {n.email}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-mono-tabular text-sm text-text">{(n.share_bps / 100).toFixed(0)}%</span>
                <Badge variant={n.invite_status === "accepted" ? "success" : "outline"}>
                  {n.invite_status}
                </Badge>
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}

function GuardiansCard({
  guardians,
  threshold,
  loading,
}: {
  vaultLoaded: boolean;
  guardians: NonNullable<ReturnType<typeof useVault>["data"]>["guardians"];
  threshold: number;
  loading: boolean;
}) {
  const [open, setOpen] = useState(false);
  const invite = useInviteGuardian();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<GuardianForm>({ resolver: zodResolver(guardianSchema) });

  async function onSubmit(values: GuardianForm) {
    try {
      await invite.mutateAsync(values);
      toast.success(`Invite sent to ${values.name}`);
      reset();
      setOpen(false);
    } catch {
      toast.error("Could not send invite — check the backend connection.");
    }
  }

  const accepted = guardians.filter((g) => g.status === "accepted").length;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="flex items-center gap-2">
            <Users className="size-4" /> Guardians
          </CardTitle>
          <CardDescription>
            {accepted}/{guardians.length || 0} accepted · needs {threshold} of {guardians.length || "N"} to confirm
          </CardDescription>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button size="sm" variant="outline">
              <Plus className="size-4" /> Add
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Invite a guardian</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
              <div className="space-y-1.5">
                <Label htmlFor="g-name">Full name</Label>
                <Input id="g-name" {...register("name")} />
                {errors.name && <p className="text-xs text-danger">{errors.name.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="g-relation">Relation</Label>
                <Input id="g-relation" placeholder="Brother, friend, family doctor…" {...register("relation")} />
                {errors.relation && <p className="text-xs text-danger">{errors.relation.message}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="g-email">Email</Label>
                <Input id="g-email" type="email" {...register("email")} />
                {errors.email && <p className="text-xs text-danger">{errors.email.message}</p>}
              </div>
              <DialogFooter>
                <Button type="submit" variant="brand" disabled={isSubmitting}>
                  Send invite
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </CardHeader>
      <CardContent className="space-y-2">
        {loading ? (
          Array.from({ length: 2 }).map((_, i) => <Skeleton key={i} className="h-14" />)
        ) : guardians.length === 0 ? (
          <EmptyState icon={Users} title="No guardians yet" body="Pick trusted people to confirm the unthinkable." />
        ) : (
          guardians.map((g) => (
            <div key={g.id} className="flex items-center justify-between rounded-lg border border-border p-3">
              <div>
                <p className="text-sm font-medium text-text">{g.name}</p>
                <p className="text-xs text-muted">
                  {g.relation} · {g.email}
                </p>
              </div>
              <Badge variant={g.status === "accepted" ? "success" : "outline"}>{g.status}</Badge>
            </div>
          ))
        )}
        <Separator className="my-1" />
        <p className="text-xs text-muted">
          Release needs {threshold} of {guardians.length || "N"} guardians to attest, then a challenge window
          you can cancel.
        </p>
      </CardContent>
    </Card>
  );
}
