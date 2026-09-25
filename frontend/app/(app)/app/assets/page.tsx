"use client";

import { useState } from "react";
import Link from "next/link";
import { motion } from "motion/react";
import { Wallet, ChevronRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/common/skeleton";
import { EmptyState } from "@/components/common/empty-state";
import { useAssets } from "@/lib/queries/assets";
import { formatCurrency } from "@/lib/format";
import type { NomineeStatus } from "@/lib/types";

const FILTERS = [
  { value: "all", label: "All" },
  { value: "term_life", label: "Life" },
  { value: "health", label: "Health" },
  { value: "fd", label: "FDs" },
  { value: "mutual_fund", label: "Funds" },
  { value: "loan", label: "Loans" },
];

const NOMINEE_BADGE: Record<NomineeStatus, "success" | "destructive" | "warning" | "outline"> = {
  ok: "success",
  missing: "destructive",
  outdated: "warning",
  unknown: "outline",
};

export default function AssetsPage() {
  const [filter, setFilter] = useState("all");
  const { data: assets, isLoading } = useAssets(filter === "all" ? undefined : { type: filter });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-text sm:text-3xl">Your assets</h1>
        <p className="text-sm text-muted">Everything Virasat has found and confirmed for you.</p>
      </div>

      <Tabs value={filter} onValueChange={setFilter}>
        <TabsList className="flex-wrap h-auto">
          {FILTERS.map((f) => (
            <TabsTrigger key={f.value} value={f.value}>
              {f.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
      ) : !assets || assets.length === 0 ? (
        <EmptyState
          icon={Wallet}
          title="No assets here yet"
          body="Try Discover to scan a statement, SMS, or your Paytm feed."
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {assets.map((asset) => (
            <Link key={asset.id} href={`/app/assets/${asset.id}`}>
              <motion.div layoutId={`asset-${asset.id}`}>
                <Card className="transition-shadow hover:shadow-[0_4px_28px_rgba(0,46,110,0.14)]">
                  <CardContent className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-display font-semibold text-text">{asset.label}</p>
                      <p className="text-xs text-muted">
                        {asset.institution_name ?? "Institution"} ·{" "}
                        {asset.value_estimate ? formatCurrency(asset.value_estimate, { compact: true }) : "—"}
                      </p>
                      <Badge variant={NOMINEE_BADGE[asset.nominee_status]} className="mt-2">
                        {asset.nominee_status === "ok" ? "Nominee set" : asset.nominee_status}
                      </Badge>
                    </div>
                    <ChevronRight className="size-4 text-muted" />
                  </CardContent>
                </Card>
              </motion.div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
