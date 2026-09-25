"use client";

import { use, useEffect, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { LogIn, ShieldCheck, KeyRound, Download } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { createClient } from "@/lib/supabase/client";
import { api, ApiError } from "@/lib/api";
import { toast } from "sonner";

interface AcceptResult {
  role: "nominee" | "guardian";
  vault_id: string;
  legacy_key_share?: string;
}

export default function InvitePage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = use(params);
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [accepting, setAccepting] = useState(false);
  const [result, setResult] = useState<AcceptResult | null>(null);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data }) => setAuthed(!!data.user));
  }, []);

  async function handleGoogleSignIn() {
    const supabase = createClient();
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/auth/callback?next=/invite/${token}` },
    });
  }

  async function handleAccept() {
    setAccepting(true);
    try {
      const res = await api.post<AcceptResult>(`/invites/${token}/accept`);
      setResult(res);
      toast.success("Invite accepted");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not accept the invite right now.";
      toast.error(message);
    } finally {
      setAccepting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg px-4 py-12">
      <Card className="w-full max-w-md">
        <CardHeader className="items-center text-center">
          <div className="flex size-12 items-center justify-center rounded-full bg-cyan-soft text-brand-navy dark:text-brand-cyan">
            <ShieldCheck className="size-6" />
          </div>
          <CardTitle>You&apos;ve been invited to Virasat</CardTitle>
          <CardDescription>Someone trusts you to help protect their family&apos;s future.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {result ? (
            <div className="space-y-4 text-center">
              <p className="text-sm text-text">
                You&apos;re now a {result.role} on this vault. {result.role === "nominee" && "Keep your Legacy Key safe — you'll need it after release."}
              </p>
              {result.legacy_key_share && (
                <div className="glass-surface mx-auto flex w-fit flex-col items-center gap-3 rounded-2xl border border-border bg-navy-950 p-5 text-white">
                  <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-gold">
                    <KeyRound className="size-3.5" /> Legacy Key
                  </p>
                  <div className="rounded-xl bg-white p-3">
                    <QRCodeSVG value={result.legacy_key_share} size={160} />
                  </div>
                  <Button size="sm" variant="outline" className="border-white/25 text-white hover:bg-white/10">
                    <Download className="size-3.5" /> Download card
                  </Button>
                </div>
              )}
              <Button asChild variant="brand" className="w-full">
                <a href={result.role === "nominee" ? `/nominee/${result.vault_id}` : `/guardian/${result.vault_id}`}>
                  Continue
                </a>
              </Button>
            </div>
          ) : authed === null ? (
            <div className="h-24 animate-pulse rounded-xl bg-surface-2" />
          ) : authed ? (
            <Button variant="brand" className="w-full" onClick={handleAccept} disabled={accepting}>
              {accepting ? "Accepting…" : "Accept invite"}
            </Button>
          ) : (
            <Button variant="brand" className="w-full" onClick={handleGoogleSignIn}>
              <LogIn className="size-4" /> Continue with Google
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
