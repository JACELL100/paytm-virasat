import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { ArrowRight } from "lucide-react";
import { Reveal } from "@/components/motion/reveal";
import { Button } from "@/components/ui/button";

export async function CtaSection() {
  const t = await getTranslations("marketing.cta");

  return (
    <section className="mx-auto max-w-[1200px] px-4 pb-20 sm:px-6">
      <Reveal className="relative overflow-hidden rounded-[var(--radius-hero)] brand-gradient px-6 py-16 text-center text-white sm:px-12">
        <div className="pointer-events-none absolute inset-0 opacity-40 [background:radial-gradient(50%_60%_at_20%_100%,rgba(233,180,76,0.25),transparent)]" />
        <h2 className="relative font-display text-3xl font-bold sm:text-4xl">{t("title")}</h2>
        <p className="relative mt-3 text-white/80">{t("subtitle")}</p>
        <Button asChild size="lg" className="relative mt-8 bg-white text-brand-navy hover:bg-white/90">
          <Link href="/login">
            {t("button")}
            <ArrowRight className="size-4" />
          </Link>
        </Button>
      </Reveal>
    </section>
  );
}
