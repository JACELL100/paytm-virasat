import { getTranslations } from "next-intl/server";

export async function MarketingFooter() {
  const t = await getTranslations("marketing.footer");
  const tc = await getTranslations("common");

  return (
    <footer className="border-t border-border bg-surface-2/60 py-8">
      <div className="mx-auto flex max-w-[1200px] flex-col items-center gap-2 px-4 text-center text-xs text-muted sm:px-6">
        <p className="font-medium text-text">{tc("appName")}</p>
        <p>{t("rights")}</p>
        <p>{t("disclaimer")}</p>
      </div>
    </footer>
  );
}
