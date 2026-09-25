import { Hero } from "@/components/marketing/hero";
import { HowItWorks } from "@/components/marketing/how-it-works";
import { TrustSection } from "@/components/marketing/trust-section";
import { Faq } from "@/components/marketing/faq";
import { CtaSection } from "@/components/marketing/cta-section";
import { MarketingFooter } from "@/components/marketing/footer";

export default function LandingPage() {
  return (
    <>
      <Hero />
      <HowItWorks />
      <TrustSection />
      <Faq />
      <CtaSection />
      <MarketingFooter />
    </>
  );
}
