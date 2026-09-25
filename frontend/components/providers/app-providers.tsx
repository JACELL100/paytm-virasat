"use client";

import { NextIntlClientProvider } from "next-intl";
import { MotionConfig } from "motion/react";
import { Toaster } from "@/components/ui/sonner";
import { QueryProvider } from "@/components/providers/query-provider";
import { ThemeProvider } from "@/components/providers/theme-provider";

export function AppProviders({
  children,
  locale,
  messages,
}: {
  children: React.ReactNode;
  locale: string;
  messages: Record<string, unknown>;
}) {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <NextIntlClientProvider locale={locale} messages={messages}>
        {/* reducedMotion="user" makes every Motion animation in the app respect
            prefers-reduced-motion automatically (Implementation Plan §6.4). */}
        <MotionConfig reducedMotion="user">
          <QueryProvider>
            {children}
            <Toaster richColors position="top-center" />
          </QueryProvider>
        </MotionConfig>
      </NextIntlClientProvider>
    </ThemeProvider>
  );
}
