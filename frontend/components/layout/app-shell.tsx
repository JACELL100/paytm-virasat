"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  LayoutDashboard,
  Search,
  Wallet,
  FileText,
  ShieldCheck,
  Activity as ActivityIcon,
  LogOut,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { LanguageSwitcher } from "@/components/layout/language-switcher";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { Button } from "@/components/ui/button";
import { createClient } from "@/lib/supabase/client";

const NAV_ITEMS = [
  { href: "/app", key: "dashboard", icon: LayoutDashboard },
  { href: "/app/discover", key: "discover", icon: Search },
  { href: "/app/assets", key: "assets", icon: Wallet },
  { href: "/app/documents", key: "documents", icon: FileText },
  { href: "/app/vault", key: "vault", icon: ShieldCheck },
  { href: "/app/activity", key: "activity", icon: ActivityIcon },
] as const;

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const t = useTranslations("nav");
  const tc = useTranslations("common");

  async function handleSignOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/");
    router.refresh();
  }

  return (
    <div className="min-h-screen bg-bg">
      {/* Top bar */}
      <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-border bg-surface/80 px-4 backdrop-blur-md sm:px-6 md:pl-24">
        <Link href="/app" className="flex items-center gap-2">
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

      {/* Desktop floating side rail */}
      <nav className="fixed top-1/2 left-4 z-30 hidden -translate-y-1/2 flex-col gap-1 rounded-2xl border border-border bg-surface/90 p-2 shadow-soft backdrop-blur-md md:flex">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex size-12 flex-col items-center justify-center gap-0.5 rounded-xl text-[10px] font-medium transition-colors",
                active
                  ? "bg-cyan-soft text-brand-navy dark:text-brand-cyan"
                  : "text-muted hover:bg-surface-2 hover:text-text",
              )}
              title={t(item.key)}
            >
              <Icon className="size-5" />
            </Link>
          );
        })}
      </nav>

      <main className="mx-auto max-w-[1200px] px-4 pb-24 pt-6 sm:px-6 md:pb-10 md:pl-24">
        {children}
      </main>

      {/* Mobile bottom tab bar */}
      <nav className="fixed inset-x-0 bottom-0 z-30 flex h-16 items-center justify-around border-t border-border bg-surface/95 backdrop-blur-md md:hidden">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex min-w-11 flex-col items-center justify-center gap-1 rounded-lg px-2 py-1.5 text-[10px] font-medium",
                active ? "text-brand-cyan" : "text-muted",
              )}
            >
              <Icon className="size-5" />
              {t(item.key)}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
