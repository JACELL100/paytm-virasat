"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import NumberFlow from "@number-flow/react";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import { Button } from "@/components/ui/button";
import { PulseLine } from "@/components/vault/pulse-line";

export function Hero() {
  const t = useTranslations("marketing.hero");
  const reduceMotion = useReducedMotion();

  return (
    <section className="relative overflow-hidden brand-gradient text-white">
      <div className="pointer-events-none absolute inset-0 opacity-40 [background:radial-gradient(60%_50%_at_80%_0%,rgba(0,186,242,0.35),transparent)]" />
      <div className="relative mx-auto flex max-w-[1200px] flex-col items-center gap-10 px-4 py-20 text-center sm:px-6 md:py-28">
        <motion.div
          initial={reduceMotion ? { opacity: 1 } : { opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-4 py-1.5 text-xs font-medium text-white/90"
        >
          <ShieldCheck className="size-3.5" />
          {t("eyebrow")}
        </motion.div>

        <motion.h1
          initial={reduceMotion ? { opacity: 1 } : { opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.05 }}
          className="max-w-3xl font-display text-4xl font-extrabold tracking-tight sm:text-5xl md:text-6xl"
        >
          {t("title")}
        </motion.h1>

        <motion.p
          initial={reduceMotion ? { opacity: 1 } : { opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="max-w-2xl text-base text-white/85 sm:text-lg"
        >
          {t("subtitle")}
        </motion.p>

        <motion.div
          initial={reduceMotion ? { opacity: 1 } : { opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.15 }}
          className="flex flex-col gap-3 sm:flex-row"
        >
          <Button asChild size="lg" className="bg-white text-brand-navy hover:bg-white/90">
            <Link href="/login">
              {t("ctaPrimary")}
              <ArrowRight className="size-4" />
            </Link>
          </Button>
          <Button asChild size="lg" variant="outline" className="border-white/25 text-white hover:bg-white/10">
            <a href="#how-it-works">{t("ctaSecondary")}</a>
          </Button>
        </motion.div>

        {/* Pulse line motif */}
        <motion.div
          initial={reduceMotion ? { opacity: 1 } : { opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mt-4 w-full max-w-xl"
        >
          <PulseLine status="active" className="[--brand-cyan:#5EE6FF]" />
        </motion.div>

        {/* Unclaimed money stat hook */}
        <motion.div
          initial={reduceMotion ? { opacity: 1 } : { opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.25 }}
          className="glass-surface mt-6 flex w-full max-w-md flex-col items-center gap-1 rounded-2xl px-6 py-5"
        >
          <div className="flex items-baseline gap-1 font-mono-tabular text-3xl font-bold text-gold sm:text-4xl">
            ₹
            <NumberFlow value={83000} suffix=" Cr+" />
          </div>
          <p className="text-xs text-white/70">{t("statLabel")}</p>
          <p className="text-[10px] text-white/40">{t("statSource")}</p>
        </motion.div>
      </div>
    </section>
  );
}
