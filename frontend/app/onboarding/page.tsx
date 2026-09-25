"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "motion/react";
import { Languages, ShieldCheck, Users, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { setLocaleCookie, type AppLocale } from "@/i18n/locales";
import { toast } from "sonner";

const LANGUAGES: { code: AppLocale; label: string; native: string }[] = [
  { code: "en", label: "English", native: "English" },
  { code: "hi", label: "Hindi", native: "हिंदी" },
  { code: "mr", label: "Marathi", native: "मराठी" },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [language, setLanguage] = useState<AppLocale>("en");
  const [intent, setIntent] = useState<"owner" | "invitee" | null>(null);
  const [consent, setConsent] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const steps = ["Language", "Your goal", "Consent"];

  async function finish() {
    setSubmitting(true);
    setLocaleCookie(language);
    try {
      await api.patch("/me", { language });
      await api.post("/me/consents", { purpose: "core_service", version: "1.0" });
    } catch {
      // Backend may not be live yet during early development — proceed anyway.
    }
    toast.success("You're all set");
    router.push(intent === "invitee" ? "/nominee" : "/app");
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg px-4 py-12">
      <Card className="w-full max-w-lg">
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between">
            {steps.map((label, i) => (
              <div key={label} className="flex flex-1 items-center">
                <div
                  className={cn(
                    "flex size-8 items-center justify-center rounded-full text-xs font-semibold",
                    i <= step ? "brand-gradient text-white" : "bg-surface-2 text-muted",
                  )}
                >
                  {i < step ? <Check className="size-4" /> : i + 1}
                </div>
                {i < steps.length - 1 && (
                  <div className={cn("mx-2 h-0.5 flex-1", i < step ? "bg-brand-cyan" : "bg-border")} />
                )}
              </div>
            ))}
          </div>

          <AnimatePresence mode="wait">
            {step === 0 && (
              <motion.div key="lang" initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -16 }} className="space-y-4">
                <div className="flex items-center gap-2">
                  <Languages className="size-5 text-brand-cyan" />
                  <h2 className="font-display text-lg font-semibold">Choose your language</h2>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  {LANGUAGES.map((l) => (
                    <button
                      key={l.code}
                      onClick={() => setLanguage(l.code)}
                      className={cn(
                        "rounded-xl border p-4 text-center transition-colors",
                        language === l.code
                          ? "border-brand-cyan bg-cyan-soft"
                          : "border-border hover:bg-surface-2",
                      )}
                    >
                      <p className="font-display font-semibold">{l.native}</p>
                      <p className="text-xs text-muted">{l.label}</p>
                    </button>
                  ))}
                </div>
              </motion.div>
            )}

            {step === 1 && (
              <motion.div key="intent" initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -16 }} className="space-y-4">
                <div className="flex items-center gap-2">
                  <Users className="size-5 text-brand-cyan" />
                  <h2 className="font-display text-lg font-semibold">What brings you here?</h2>
                </div>
                <div className="grid gap-3">
                  <button
                    onClick={() => setIntent("owner")}
                    className={cn(
                      "rounded-xl border p-4 text-left transition-colors",
                      intent === "owner" ? "border-brand-cyan bg-cyan-soft" : "border-border hover:bg-surface-2",
                    )}
                  >
                    <p className="font-display font-semibold">Secure my family</p>
                    <p className="text-sm text-muted">I want to discover my assets and set up a Virasat vault.</p>
                  </button>
                  <button
                    onClick={() => setIntent("invitee")}
                    className={cn(
                      "rounded-xl border p-4 text-left transition-colors",
                      intent === "invitee" ? "border-brand-cyan bg-cyan-soft" : "border-border hover:bg-surface-2",
                    )}
                  >
                    <p className="font-display font-semibold">I was invited</p>
                    <p className="text-sm text-muted">I&apos;m a nominee or guardian for someone else&apos;s vault.</p>
                  </button>
                </div>
              </motion.div>
            )}

            {step === 2 && (
              <motion.div key="consent" initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -16 }} className="space-y-4">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="size-5 text-brand-cyan" />
                  <h2 className="font-display text-lg font-semibold">Your consent, on your terms</h2>
                </div>
                <p className="text-sm text-muted">
                  Under the DPDP Act, 2023, we ask for explicit, purpose-specific consent before processing your
                  financial documents and personal data. You can withdraw this anytime from Settings.
                </p>
                <label className="flex items-start gap-3 rounded-xl border border-border p-4">
                  <input
                    type="checkbox"
                    checked={consent}
                    onChange={(e) => setConsent(e.target.checked)}
                    className="mt-1 size-4 accent-[var(--brand-cyan)]"
                  />
                  <span className="text-sm">
                    I consent to Virasat processing my documents and statements to discover assets, compute my
                    Legacy Score, and seal an encrypted vault for my nominees.
                  </span>
                </label>
              </motion.div>
            )}
          </AnimatePresence>

          <div className="flex justify-between pt-2">
            <Button variant="ghost" disabled={step === 0} onClick={() => setStep((s) => s - 1)}>
              Back
            </Button>
            {step < 2 ? (
              <Button
                variant="brand"
                disabled={step === 1 && !intent}
                onClick={() => setStep((s) => s + 1)}
              >
                Continue
              </Button>
            ) : (
              <Button variant="brand" disabled={!consent || submitting} onClick={finish}>
                {submitting ? "Setting up…" : "Finish"}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
