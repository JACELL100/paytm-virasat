import { getTranslations } from "next-intl/server";
import { Search, ShieldCheck, HeartHandshake } from "lucide-react";
import { Reveal, StaggerGroup, StaggerItem } from "@/components/motion/reveal";

export async function HowItWorks() {
  const t = await getTranslations("marketing.how");

  const steps = [
    { icon: Search, title: t("step1Title"), body: t("step1Body") },
    { icon: ShieldCheck, title: t("step2Title"), body: t("step2Body") },
    { icon: HeartHandshake, title: t("step3Title"), body: t("step3Body") },
  ];

  return (
    <section id="how-it-works" className="mx-auto max-w-[1200px] px-4 py-20 sm:px-6">
      <Reveal className="mx-auto max-w-2xl text-center">
        <h2 className="font-display text-3xl font-bold text-text sm:text-4xl">{t("title")}</h2>
        <p className="mt-3 text-muted">{t("subtitle")}</p>
      </Reveal>

      <StaggerGroup className="mt-14 grid gap-6 md:grid-cols-3">
        {steps.map((step, i) => (
          <StaggerItem key={step.title}>
            <div className="relative h-full rounded-2xl border border-border bg-surface p-7 shadow-soft">
              <span className="absolute -top-4 -left-2 font-display text-6xl font-extrabold text-cyan-soft select-none">
                {i + 1}
              </span>
              <div className="relative flex size-11 items-center justify-center rounded-xl brand-gradient text-white">
                <step.icon className="size-5" />
              </div>
              <h3 className="relative mt-5 font-display text-lg font-semibold text-text">
                {step.title}
              </h3>
              <p className="relative mt-2 text-sm text-muted">{step.body}</p>
            </div>
          </StaggerItem>
        ))}
      </StaggerGroup>
    </section>
  );
}
