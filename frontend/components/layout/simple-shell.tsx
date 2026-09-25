"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";
import { useTranslations } from "next-intl";
import { LanguageSwitcher } from "@/components/layout/language-switcher";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { Button } from "@/components/ui/button";
import { createClient } from "@/lib/supabase/client";

export function SimpleShell({
  children,
  homeHref = "/app",
}: {
  children: React.ReactNode;
  homeHref?: string;
}) {
  const router = useRouter();
  const tc = useTranslations("common");

  async function handleSignOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/");
    router.refresh();
  }

  return (
    <div className="min-h-screen bg-bg">
      <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-border bg-surface/80 px-4 backdrop-blur-md sm:px-6">
        <Link href={homeHref} className="flex items-center gap-2">
          <span className="flex size-8 items-center justify-center rounded-lg brand-gradient text-sm font-bold text-white">
            V
          </span>
          <span className="font-display font-semibold text-text">{tc("appName")}</span>
        </Link>
        <div className="flex items-center gap-2">
          <LanguageSwitcher />
          <ThemeToggle />
          <Button variant="ghost" size="icon" aria-label={tc("signOut")} onClick={handleSignOut}>
            <LogOut className="size-4" />
          </Button>
        </div>
      </header>
      <main className="mx-auto max-w-[1000px] px-4 py-6 sm:px-6">{children}</main>
    </div>
  );
}
