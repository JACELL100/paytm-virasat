"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { toast } from "sonner";
import { FileUp, MessageSquareText, Wallet2, Check, X, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { EmptyState } from "@/components/common/empty-state";
import {
  useUploadStatement,
  usePasteSms,
  useConnectPaytmFeed,
  useAcceptSuggestion,
  useRejectSuggestion,
} from "@/lib/queries/assets";
import type { DiscoverySuggestion } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function DiscoverPage() {
  const [suggestions, setSuggestions] = useState<DiscoverySuggestion[]>([]);
  const uploadStatement = useUploadStatement();
  const pasteSms = usePasteSms();
  const connectFeed = useConnectPaytmFeed();
  const accept = useAcceptSuggestion();
  const reject = useRejectSuggestion();
  const [smsText, setSmsText] = useState("");

  function mergeSuggestions(next: DiscoverySuggestion[]) {
    setSuggestions((prev) => [...next, ...prev]);
  }

  const onDrop = useCallback(
    async (files: File[]) => {
      const file = files[0];
      if (!file) return;
      try {
        const res = await uploadStatement.mutateAsync(file);
        mergeSuggestions(res);
        toast.success(`Found ${res.length} possible assets`);
      } catch {
        toast.error("Could not reach the backend yet — try again once it's running.");
      }
    },
    [uploadStatement],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"], "text/csv": [".csv"] },
    maxSize: 10 * 1024 * 1024,
    multiple: false,
  });

  async function handleSms() {
    if (!smsText.trim()) return;
    try {
      const res = await pasteSms.mutateAsync(smsText);
      mergeSuggestions(res);
      toast.success(`Found ${res.length} possible assets`);
      setSmsText("");
    } catch {
      toast.error("Could not reach the backend yet — try again once it's running.");
    }
  }

  async function handleFeed() {
    try {
      const res = await connectFeed.mutateAsync();
      mergeSuggestions(res);
      toast.success(`Found ${res.length} possible assets from your Paytm feed`);
    } catch {
      toast.error("Could not reach the backend yet — try again once it's running.");
    }
  }

  async function handleAccept(id: string) {
    setSuggestions((prev) => prev.map((s) => (s.id === id ? { ...s, status: "accepted" } : s)));
    try {
      await accept.mutateAsync(id);
    } catch {
      // optimistic UI stays; backend not live yet
    }
  }

  async function handleReject(id: string) {
    setSuggestions((prev) => prev.map((s) => (s.id === id ? { ...s, status: "rejected" } : s)));
    try {
      await reject.mutateAsync(id);
    } catch {
      // optimistic UI stays
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-text sm:text-3xl">Discover your assets</h1>
        <p className="text-sm text-muted">
          Bring in a statement, paste your SMS, or connect your Paytm feed — we&apos;ll find what&apos;s yours.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <FileUp className="size-4" /> Upload statement
            </CardTitle>
            <CardDescription>Bank statement, PDF or CSV</CardDescription>
          </CardHeader>
          <CardContent>
            <div
              {...getRootProps()}
              className={cn(
                "flex h-28 cursor-pointer flex-col items-center justify-center gap-1 rounded-xl border-2 border-dashed text-center text-xs text-muted transition-colors",
                isDragActive ? "border-brand-cyan bg-cyan-soft" : "border-border hover:bg-surface-2",
              )}
            >
              <input {...getInputProps()} />
              {uploadStatement.isPending ? (
                <Loader2 className="size-5 animate-spin text-brand-cyan" />
              ) : (
                <>
                  <FileUp className="size-5" />
                  <span>Drag & drop, or click to browse</span>
                </>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <MessageSquareText className="size-4" /> Paste SMS
            </CardTitle>
            <CardDescription>Bank / insurer alerts</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <Textarea
              value={smsText}
              onChange={(e) => setSmsText(e.target.value)}
              placeholder="Paste one or more SMS texts here…"
              className="h-16 text-xs"
            />
            <Button size="sm" variant="outline" className="w-full" onClick={handleSms} disabled={pasteSms.isPending}>
              {pasteSms.isPending ? <Loader2 className="size-4 animate-spin" /> : "Scan SMS"}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Wallet2 className="size-4" /> Connect Paytm feed
            </CardTitle>
            <CardDescription>Simulated demo transaction feed</CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              size="sm"
              variant="brand"
              className="w-full"
              onClick={handleFeed}
              disabled={connectFeed.isPending}
            >
              {connectFeed.isPending ? <Loader2 className="size-4 animate-spin" /> : "Pull my Paytm activity"}
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Suggestions</CardTitle>
          <CardDescription>Review and accept what looks right — you&apos;re always in control.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {suggestions.length === 0 ? (
            <EmptyState
              icon={Wallet2}
              title="No suggestions yet"
              body="Use one of the three sources above to start finding your assets."
            />
          ) : (
            suggestions.map((s) => (
              <div
                key={s.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border p-3.5"
              >
                <div>
                  <p className="text-sm font-medium text-text">{s.payload.label}</p>
                  <p className="text-xs text-muted">
                    {s.payload.institution_name ?? "Unknown institution"} ·{" "}
                    {s.payload.amount ? `₹${s.payload.amount.toLocaleString("en-IN")}` : "—"}{" "}
                    {s.payload.frequency ? `/ ${s.payload.frequency}` : ""}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="outline">{Math.round(s.payload.confidence * 100)}% confident</Badge>
                  {s.status === "pending" ? (
                    <>
                      <Button size="icon" variant="outline" className="size-8" onClick={() => handleAccept(s.id)}>
                        <Check className="size-4 text-success" />
                      </Button>
                      <Button size="icon" variant="outline" className="size-8" onClick={() => handleReject(s.id)}>
                        <X className="size-4 text-danger" />
                      </Button>
                    </>
                  ) : (
                    <Badge variant={s.status === "accepted" ? "success" : "outline"}>{s.status}</Badge>
                  )}
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
