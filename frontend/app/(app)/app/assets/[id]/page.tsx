"use client";

import { use, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "motion/react";
import { ArrowLeft, FileText, MessageCircleQuestion, Send } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/common/skeleton";
import { useAsset, useAskAboutAsset } from "@/lib/queries/assets";
import { formatCurrency } from "@/lib/format";

export default function AssetDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const { data: asset, isLoading } = useAsset(id);
  const ask = useAskAboutAsset(id);
  const [question, setQuestion] = useState("");
  const [answers, setAnswers] = useState<Array<{ q: string; a: string }>>([]);

  async function handleAsk() {
    if (!question.trim()) return;
    const q = question;
    setQuestion("");
    try {
      const res = await ask.mutateAsync(q);
      setAnswers((prev) => [...prev, { q, a: res.answer }]);
    } catch {
      setAnswers((prev) => [
        ...prev,
        { q, a: "The backend isn't reachable yet, so I can't answer that right now." },
      ]);
    }
  }

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" onClick={() => router.back()} className="-ml-2">
        <ArrowLeft className="size-4" /> Back
      </Button>

      <motion.div layoutId={`asset-${id}`}>
        <Card>
          <CardHeader>
            {isLoading ? (
              <Skeleton className="h-7 w-48" />
            ) : (
              <CardTitle className="text-xl">{asset?.label ?? "Asset"}</CardTitle>
            )}
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            {isLoading ? (
              Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-14" />)
            ) : (
              <>
                <Field label="Institution" value={asset?.institution_name ?? "—"} />
                <Field
                  label="Estimated value"
                  value={asset?.value_estimate ? formatCurrency(asset.value_estimate) : "—"}
                />
                <Field
                  label="Premium / contribution"
                  value={asset?.premium_amount ? `${formatCurrency(asset.premium_amount)} / ${asset?.frequency ?? ""}` : "—"}
                />
                <Field
                  label="Nominee status"
                  value={
                    <Badge variant={asset?.nominee_status === "ok" ? "success" : "warning"}>
                      {asset?.nominee_status}
                    </Badge>
                  }
                />
              </>
            )}
          </CardContent>
        </Card>
      </motion.div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <FileText className="size-4" /> Linked documents
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted">
            Upload the policy document from{" "}
            <a href="/app/documents" className="text-brand-cyan underline">
              Documents
            </a>{" "}
            to see extracted fields and citations here.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <MessageCircleQuestion className="size-4" /> Ask about this policy
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {answers.map((entry, i) => (
            <div key={i} className="space-y-1 rounded-lg bg-surface-2/60 p-3 text-sm">
              <p className="font-medium text-text">{entry.q}</p>
              <p className="text-muted">{entry.a}</p>
            </div>
          ))}
          <div className="flex gap-2">
            <Input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. What documents do I need to claim this?"
              onKeyDown={(e) => e.key === "Enter" && handleAsk()}
            />
            <Button onClick={handleAsk} disabled={ask.isPending}>
              <Send className="size-4" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-border p-3.5">
      <p className="text-xs text-muted">{label}</p>
      <div className="mt-1 font-medium text-text">{value}</div>
    </div>
  );
}
