import { getTranslations } from "next-intl/server";
import { Link2, Lock, UserCheck } from "lucide-react";
import { Reveal, StaggerGroup, StaggerItem } from "@/components/motion/reveal";

export async function TrustSection() {
  const t = await getTranslations("marketing.trust");

  const points = [
    { icon: Link2, title: t("point1Title"), body: t("point1Body") },
    { icon: Lock, title: t("point2Title"), body: t("point2Body") },
    { icon: UserCheck, title: t("point3Title"), body: t("point3Body") },
  ];

  return (
    <section id="trust" className="bg-surface-2/60 py-20">
      <div className="mx-auto max-w-[1200px] px-4 sm:px-6">
        <Reveal className="mx-auto max-w-2xl text-center">
          <h2 className="font-display text-3xl font-bold text-text sm:text-4xl">{t("title")}</h2>
          <p className="mt-3 text-muted">{t("subtitle")}</p>
        </Reveal>

        <StaggerGroup className="mt-14 grid gap-6 md:grid-cols-3">
          {points.map((point) => (
            <StaggerItem key={point.title}>
              <div className="h-full rounded-2xl border border-border bg-surface p-7 shadow-soft">
                <div className="flex size-11 items-center justify-center rounded-xl bg-cyan-soft text-brand-navy dark:text-brand-cyan">
                  <point.icon className="size-5" />
                </div>
                <h3 className="mt-5 font-display text-lg font-semibold text-text">{point.title}</h3>
                <p className="mt-2 text-sm text-muted">{point.body}</p>
              </div>
            </StaggerItem>
          ))}
        </StaggerGroup>

        <Reveal delay={0.1} className="mx-auto mt-10 max-w-2xl rounded-xl border border-border bg-surface px-5 py-4 text-center text-xs text-muted">
          {t("disclaimer")}
        </Reveal>
      </div>
    </section>
  );
}
