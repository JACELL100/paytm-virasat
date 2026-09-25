"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { LogIn, ShieldCheck } from "lucide-react";
import { motion } from "motion/react";
import { Button } from "@/components/ui/button";
import { createClient } from "@/lib/supabase/client";

function LoginCard() {
  const [loading, setLoading] = useState(false);
  const searchParams = useSearchParams();
  const next = searchParams.get("next") ?? "/app";

  async function handleGoogleSignIn() {
    setLoading(true);
    const supabase = createClient();
    const redirectTo = `${window.location.origin}/auth/callback?next=${encodeURIComponent(next)}`;
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo },
    });
    if (error) setLoading(false);
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="glass-surface w-full max-w-sm rounded-[var(--radius-hero)] p-8 text-center text-white"
    >
      <div className="mx-auto flex size-12 items-center justify-center rounded-xl bg-white/10">
        <ShieldCheck className="size-6" />
      </div>
      <h1 className="mt-5 font-display text-2xl font-bold">Welcome to Virasat</h1>
      <p className="mt-2 text-sm text-white/75">
        Sign in with the same Google account you use for Paytm. No passwords, no new wallet.
      </p>
      <Button
        onClick={handleGoogleSignIn}
        disabled={loading}
        size="lg"
        className="mt-8 w-full bg-white text-brand-navy hover:bg-white/90"
      >
        <LogIn className="size-4" />
        {loading ? "Redirecting…" : "Continue with Google"}
      </Button>
      <p className="mt-6 text-xs text-white/50">
        By continuing you agree to Virasat&apos;s data handling under the DPDP Act, 2023. Read our{" "}
        <Link href="/" className="underline underline-offset-2">
          disclosures
        </Link>
        .
      </p>
    </motion.div>
  );
}

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center brand-gradient px-4 py-16">
      <Suspense fallback={null}>
        <LoginCard />
      </Suspense>
    </div>
  );
}
