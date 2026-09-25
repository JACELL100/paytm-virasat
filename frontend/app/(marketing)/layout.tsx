import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { Button } from "@/components/ui/button";
import { LanguageSwitcher } from "@/components/layout/language-switcher";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { SmoothScroll } from "@/components/motion/smooth-scroll";

export default async function MarketingLayout({ children }: { children: React.ReactNode }) {
  const t = await getTranslations("marketing.nav");
  const tc = await getTranslations("common");

  return (
    <SmoothScroll>
      <div className="flex min-h-screen flex-col">
        <header className="sticky top-0 z-40 border-b border-white/5 bg-navy-950/70 backdrop-blur-md">
          <div className="mx-auto flex h-16 max-w-[1200px] items-center justify-between px-4 sm:px-6">
            <Link href="/" className="flex items-center gap-2">
              <span className="flex size-8 items-center justify-center rounded-lg brand-gradient text-sm font-bold text-white">
                V
              </span>
              <span className="font-display font-semibold text-white">{tc("appName")}</span>
            </Link>
            <nav className="hidden items-center gap-6 text-sm text-white/80 md:flex">
              <a href="#how-it-works" className="hover:text-white">
                {t("howItWorks")}
              </a>
              <a href="#trust" className="hover:text-white">
                {t("trust")}
              </a>
              <a href="#faq" className="hover:text-white">
                {t("faq")}
              </a>
            </nav>
            <div className="flex items-center gap-2 [&_button]:text-white [&_button:hover]:bg-white/10">
              <LanguageSwitcher />
              <ThemeToggle />
              <Button asChild variant="ghost" className="hidden text-white hover:bg-white/10 sm:inline-flex">
                <Link href="/login">{t("login")}</Link>
              </Button>
              <Button asChild variant="brand" size="sm">
                <Link href="/login">{t("getStarted")}</Link>
              </Button>
            </div>
          </div>
        </header>
        <main className="flex-1">{children}</main>
      </div>
    </SmoothScroll>
  );
}
