import { getTranslations } from "next-intl/server";
import { Reveal } from "@/components/motion/reveal";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

export async function Faq() {
  const t = await getTranslations("marketing.faq");
  const items = [
    { q: t("q1"), a: t("a1") },
    { q: t("q2"), a: t("a2") },
    { q: t("q3"), a: t("a3") },
    { q: t("q4"), a: t("a4") },
  ];

  return (
    <section id="faq" className="mx-auto max-w-[800px] px-4 py-20 sm:px-6">
      <Reveal className="text-center">
        <h2 className="font-display text-3xl font-bold text-text sm:text-4xl">{t("title")}</h2>
      </Reveal>
      <Reveal delay={0.1} className="mt-10">
        <Accordion type="single" collapsible className="w-full">
          {items.map((item, i) => (
            <AccordionItem key={i} value={`item-${i}`}>
              <AccordionTrigger className="text-left font-display">{item.q}</AccordionTrigger>
              <AccordionContent className="text-muted">{item.a}</AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </Reveal>
    </section>
  );
}
