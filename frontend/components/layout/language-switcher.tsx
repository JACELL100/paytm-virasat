"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { Languages } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { setLocaleCookie, type AppLocale } from "@/i18n/locales";

const LOCALE_LABEL: Record<AppLocale, string> = {
  en: "English",
  hi: "हिंदी",
  mr: "मराठी",
};

export function LanguageSwitcher() {
  const locale = useLocale() as AppLocale;
  const router = useRouter();
  const t = useTranslations("common");

  function setLocale(next: AppLocale) {
    setLocaleCookie(next);
    router.refresh();
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" className="gap-1.5" aria-label={t("language")}>
          <Languages className="size-4" />
          <span className="hidden sm:inline">{LOCALE_LABEL[locale]}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {(Object.keys(LOCALE_LABEL) as AppLocale[]).map((code) => (
          <DropdownMenuItem key={code} onClick={() => setLocale(code)} className="justify-between">
            {LOCALE_LABEL[code]}
            {code === locale && <span className="text-brand-cyan">✓</span>}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
