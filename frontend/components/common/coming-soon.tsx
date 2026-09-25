import Link from "next/link";
import { Sparkles } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";

export function ComingSoon({
  title,
  description,
  backHref = "/app",
}: {
  title: string;
  description?: string;
  backHref?: string;
}) {
  const t = useTranslations("common");

  return (
    <div className="mx-auto flex min-h-[60vh] max-w-md flex-col items-center justify-center gap-5 px-6 text-center">
      <div className="flex size-16 items-center justify-center rounded-2xl brand-gradient text-white shadow-soft">
        <Sparkles className="size-7" />
      </div>
      <div className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-brand-cyan">
          {t("comingSoonTitle")}
        </p>
        <h1 className="font-display text-2xl font-bold text-text">{title}</h1>
        <p className="text-sm text-muted">{description ?? t("comingSoonBody")}</p>
      </div>
      <Button asChild variant="outline">
        <Link href={backHref}>{t("back")}</Link>
      </Button>
    </div>
  );
}
