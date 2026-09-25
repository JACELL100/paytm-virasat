"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { AlertTriangle, ArrowRight, Sparkles, Wallet } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/common/skeleton";
import { EmptyState } from "@/components/common/empty-state";
import { LegacyScoreRing } from "@/components/charts/legacy-score-ring";
import { PulseLine, type PulseLineStatus } from "@/components/vault/pulse-line";
import { useInsights } from "@/lib/queries/insights";
import { useVault } from "@/lib/queries/vault";
import { useActivity } from "@/lib/queries/activity";
import { formatCurrency, formatRelative } from "@/lib/format";
import type { AssetType, VaultState } from "@/lib/types";

const ASSET_TYPE_LABEL: Partial<Record<AssetType, string>> = {
  term_life: "Term life",
  life_endowment: "Endowment",
  ulip: "ULIP",
  health: "Health",
  motor: "Motor",
  fd: "Fixed deposits",
  savings: "Savings",
  mutual_fund: "Mutual funds",
  stocks: "Stocks",
  ppf: "PPF",
  epf: "EPF",
  nps: "NPS",
  gold: "Gold",
  loan: "Loans",
  credit_card: "Credit card",
  other: "Other",
};

const VAULT_TO_PULSE: Record<VaultState, PulseLineStatus> = {
  draft: "active",
  active: "active",
  challenge: "challenge",
  released: "released",
  revoked: "active",
};

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const { data: insights, isLoading: insightsLoading } = useInsights();
  const { data: vault, isLoading: vaultLoading } = useVault();
  const { data: activity, isLoading: activityLoading } = useActivity();

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm text-muted">{t("greeting")}</p>
        <h1 className="font-display text-2xl font-bold text-text sm:text-3xl">Rajesh</h1>
      </div>

      {/* Vault status header with Pulse Line */}
      <Card className="overflow-hidden">
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-muted">{t("vaultStatusTitle")}</p>
              {vaultLoading ? (
                <Skeleton className="mt-1 h-6 w-40" />
              ) : (
                <p className="font-display text-lg font-semibold text-text">
                  {vault ? vaultStateLabel(vault.state, t) : t("vaultDraft")}
                </p>
              )}
            </div>
            {!vault && !vaultLoading && (
              <Button asChild size="sm" variant="brand">
                <Link href="/app/vault">
                  {t("sealCta")}
                  <ArrowRight className="size-4" />
                </Link>
              </Button>
            )}
          </div>
          <PulseLine status={vault ? VAULT_TO_PULSE[vault.state] : "active"} />
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Legacy score */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>{t("legacyScoreTitle")}</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col items-center gap-3">
            {insightsLoading ? (
              <Skeleton className="size-44 rounded-full" />
            ) : (
              <LegacyScoreRing score={insights?.legacy_score ?? 0} />
            )}
            <p className="text-center text-sm text-muted">{t("legacyScoreBody")}</p>
          </CardContent>
        </Card>

        {/* Asset map + gaps */}
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>{t("assetMapTitle")}</CardTitle>
              {insights && insights.total_value > 0 && (
                <span className="font-mono-tabular text-sm font-semibold text-text">
                  {formatCurrency(insights.total_value, { compact: true })}
                </span>
              )}
            </CardHeader>
            <CardContent>
              {insightsLoading ? (
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <Skeleton key={i} className="h-16" />
                  ))}
                </div>
              ) : !insights || Object.keys(insights.asset_totals_by_type).length === 0 ? (
                <EmptyState
                  icon={Wallet}
                  title={t("assetMapEmpty")}
                  action={
                    <Button asChild size="sm" variant="brand">
                      <Link href="/app/discover">{t("assetMapCta")}</Link>
                    </Button>
                  }
                />
              ) : (
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  {Object.entries(insights.asset_totals_by_type).map(([type, value]) => (
                    <div key={type} className="rounded-xl border border-border bg-surface-2/60 p-3">
                      <p className="text-xs text-muted">{ASSET_TYPE_LABEL[type as AssetType] ?? type}</p>
                      <p className="font-mono-tabular text-sm font-semibold text-text">
                        {formatCurrency(value, { compact: true })}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t("gapsTitle")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {insightsLoading ? (
                Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-14" />)
              ) : !insights || insights.gaps.length === 0 ? (
                <EmptyState icon={Sparkles} title={t("gapsEmpty")} />
              ) : (
                insights.gaps.slice(0, 3).map((gap) => (
                  <div
                    key={gap.id}
                    className="flex items-start gap-3 rounded-xl border border-border p-3.5"
                  >
                    <AlertTriangle
                      className={
                        "mt-0.5 size-4 shrink-0 " +
                        (gap.severity === "high" ? "text-danger" : "text-warning")
                      }
                    />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-text">{gap.title}</p>
                      <p className="text-xs text-muted">{gap.detail}</p>
                    </div>
                    <Badge variant={gap.severity === "high" ? "destructive" : "warning"}>
                      {gap.severity}
                    </Badge>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Recent activity */}
      <Card>
        <CardHeader>
          <CardTitle>{t("activityTitle")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {activityLoading ? (
            Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-10" />)
          ) : !activity || activity.length === 0 ? (
            <EmptyState title={t("activityEmpty")} />
          ) : (
            activity.slice(0, 6).map((event) => (
              <div key={event.id} className="flex items-center justify-between text-sm">
                <span className="capitalize text-text">{event.kind.replace("_", " ")}</span>
                <span className="text-muted">{formatRelative(event.occurred_at)}</span>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function vaultStateLabel(state: VaultState, t: ReturnType<typeof useTranslations>) {
  switch (state) {
    case "active":
      return t("vaultActive");
    case "challenge":
      return t("vaultChallenge");
    case "released":
      return t("vaultReleased");
    case "revoked":
      return t("vaultRevoked");
    default:
      return t("vaultDraft");
  }
}
